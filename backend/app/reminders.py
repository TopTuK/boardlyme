"""Proactive Telegram reminders: a daily digest of active tasks and deadlines.

Runs as an in-process asyncio loop (wired in app.main's lifespan). Each real
Telegram user gets at most one message per day, deduplicated through the
`reminder_runs` table. Users with nothing to report are logged silently so the
digest is not recomputed on every scheduler tick.

A bot can only deliver messages to users who have interacted with it (opened
the Mini App, pressed Start, or logged in via the widget with write access).
Failed deliveries are retried on the next tick, then give up for the day only
when the run is logged — see process_daily().
"""

import asyncio
import html
import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Project, ProjectMember, ReminderRun, Stage, Task, User

logger = logging.getLogger("boardly.reminders")

DIGEST_KIND = "daily"
TELEGRAM_API_BASE = "https://api.telegram.org"
MONTHS = {
    "en": ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"),
    "ru": ("ЯНВ", "ФЕВ", "МАР", "АПР", "МАЙ", "ИЮН", "ИЮЛ", "АВГ", "СЕН", "ОКТ", "НОЯ", "ДЕК"),
}


def normalize_locale(value: str | None) -> str:
    return "ru" if value == "ru" else "en"


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------- #


def parse_daily_time(value: str) -> time:
    hh, mm = value.strip().split(":")
    return time(int(hh), int(mm))


def fmt_date(day: date, locale: str = "en") -> str:
    months = MONTHS[normalize_locale(locale)]
    return f"{months[day.month - 1]} {day.day:02d}"


def days_left(deadline: date, today: date) -> int:
    return (deadline - today).days


def deadline_label(deadline: date, today: date, locale: str = "en") -> str:
    loc = normalize_locale(locale)
    left = days_left(deadline, today)
    if loc == "ru":
        if left < 0:
            return f"{fmt_date(deadline, loc)} · просрочено на {abs(left)} дн."
        if left == 0:
            return "сегодня"
        if left == 1:
            return "завтра"
        return f"{fmt_date(deadline, loc)} · через {left} дн."
    if left < 0:
        return f"{fmt_date(deadline, loc)} · {abs(left)}d overdue"
    if left == 0:
        return "due today"
    if left == 1:
        return "due tomorrow"
    return f"{fmt_date(deadline, loc)} · in {left}d"


def classify(rows, user_id, today: date, deadline_days: int):
    """Split visible task rows into (active, deadlines) for one user.

    Active = sits in a non-backlog stage, not in a done sub-stage, not
    globally completed. Deadlines = deadline within `deadline_days`
    (overdue always included). Tasks assigned to other members are skipped;
    unassigned tasks still count.
    """
    active = []
    deadlines = []
    for task, stage, project in rows:
        if task.assignee_id not in (None, user_id):
            continue
        if not stage.is_backlog and not task.stage_done:
            active.append((project, task))
        if task.deadline is not None and days_left(task.deadline, today) <= deadline_days:
            deadlines.append((project, task))
    return active, deadlines


def render_digest(active, deadlines, today: date, locale: str = "en") -> str | None:
    """Format the digest message (HTML). Returns None when there is nothing to say."""
    if not active and not deadlines:
        return None

    loc = normalize_locale(locale)
    lines = ["<b>BOARDLY // СВОДКА</b>" if loc == "ru" else "<b>BOARDLY // DAILY</b>", ""]
    if active:
        heading = f"<b>Активные задачи: {len(active)}</b>" if loc == "ru" else f"<b>Active tasks: {len(active)}</b>"
        lines.append(heading)
        by_project: dict[str, list] = {}
        for project, task in sorted(active, key=lambda row: (row[0].name.lower(), row[1].position)):
            by_project.setdefault(project.name, []).append(task)
        for project_name, tasks in by_project.items():
            lines.append(f"▸ {html.escape(project_name)}")
            for task in tasks:
                suffix = f" — {deadline_label(task.deadline, today, loc)}" if task.deadline else ""
                lines.append(f"   • {html.escape(task.title)}{suffix}")
        lines.append("")

    if deadlines:
        overdue_count = sum(1 for _, t in deadlines if days_left(t.deadline, today) < 0)
        lines.append("<b>Дедлайны</b>" if loc == "ru" else "<b>Deadlines</b>")
        if overdue_count:
            lines.append(f"⚠ Просрочено: {overdue_count}" if loc == "ru" else f"⚠ {overdue_count} overdue")
        for project, task in sorted(deadlines, key=lambda row: (row[1].deadline, row[0].name.lower())):
            lines.append(
                f"   • {html.escape(task.title)} [{html.escape(project.name)}] — {deadline_label(task.deadline, today, loc)}"
            )

    text = "\n".join(lines)
    if len(text) > 4000:  # Telegram hard limit is 4096
        text = text[:3990] + "\n…"
    return text


# --------------------------------------------------------------------------- #
# Delivery
# --------------------------------------------------------------------------- #


async def send_telegram_message(bot_token: str, chat_id: int, text: str) -> bool:
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
    except httpx.HTTPError:
        logger.warning("Telegram request for chat %s failed", chat_id, exc_info=True)
        return False
    if response.status_code != 200:
        # 403 = user never started the bot / blocked it; 400 = malformed payload
        logger.warning("Telegram sendMessage to %s failed: %s", chat_id, response.text[:200])
        return False
    return True


async def _already_logged(db, user_id, run_date: date) -> bool:
    row = (
        await db.execute(
            select(ReminderRun).where(
                ReminderRun.kind == DIGEST_KIND,
                ReminderRun.user_id == user_id,
                ReminderRun.run_date == run_date,
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def _visible_task_rows(db, user_id):
    """All tasks of the user's projects that are not globally completed."""
    return list(
        (
            await db.execute(
                select(Task, Stage, Project)
                .join(Stage, Task.stage_id == Stage.id)
                .join(Project, Task.project_id == Project.id)
                .join(
                    ProjectMember,
                    (ProjectMember.project_id == Project.id) & (ProjectMember.user_id == user_id),
                )
                .where(Stage.is_done.is_(False))
                .order_by(Project.name, Task.position)
            )
        ).all()
    )


async def process_daily(db, now: datetime) -> int:
    """Send the daily digest to every eligible user. Returns the messages sent."""
    if not settings.reminders_enabled or not settings.bot_token:
        return 0
    daily_at = parse_daily_time(settings.reminders_daily_time)
    if (now.hour, now.minute) < (daily_at.hour, daily_at.minute):
        return 0

    today = now.date()
    sent = 0
    users = (
        await db.execute(select(User).where(User.telegram_id > 0).order_by(User.created_at))
    ).scalars().all()

    for user in users:
        try:
            if await _already_logged(db, user.id, today):
                continue
            rows = await _visible_task_rows(db, user.id)
            active, deadlines = classify(rows, user.id, today, settings.reminders_deadline_days)
            text = render_digest(active, deadlines, today, locale=user.locale)
            delivered = text is None or await send_telegram_message(settings.bot_token, user.telegram_id, text)
            if delivered:
                db.add(ReminderRun(kind=DIGEST_KIND, user_id=user.id, run_date=today))
                await db.commit()
            if text is not None and delivered:
                sent += 1
        except Exception:
            logger.exception("Daily digest failed for user %s", user.id)
    return sent


async def run_reminder_loop() -> None:
    if not settings.reminders_enabled:
        logger.info("Reminders are disabled (REMINDERS_ENABLED=0)")
        return
    if not settings.bot_token:
        logger.info("Reminders are inactive: BOT_TOKEN is not configured")
        return

    tz = ZoneInfo(settings.reminders_timezone)
    logger.info(
        "Reminder loop started: daily digest at %s (%s), checked every %s min",
        settings.reminders_daily_time,
        settings.reminders_timezone,
        settings.reminders_check_interval_min,
    )
    while True:
        try:
            async with SessionLocal() as db:
                await process_daily(db, datetime.now(tz))
        except Exception:
            logger.exception("Reminder tick failed")
        await asyncio.sleep(max(1, settings.reminders_check_interval_min) * 60)
