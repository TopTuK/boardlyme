import asyncio
import uuid
from datetime import date, datetime, time

import pytest

from app import reminders
from app.config import settings
from app.models import User


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def test_parse_daily_time():
    assert reminders.parse_daily_time("09:30") == time(9, 30)


def test_days_left_and_labels():
    today = date(2026, 10, 5)
    assert reminders.days_left(date(2026, 10, 5), today) == 0
    assert reminders.deadline_label(date(2026, 10, 5), today) == "due today"
    assert reminders.deadline_label(date(2026, 10, 6), today) == "due tomorrow"
    assert reminders.deadline_label(date(2026, 10, 8), today) == "OCT 08 · in 3d"
    assert reminders.deadline_label(date(2026, 10, 3), today) == "OCT 03 · 2d overdue"


def test_deadline_label_and_digest_in_russian():
    today = date(2026, 10, 5)
    assert reminders.deadline_label(date(2026, 10, 5), today, "ru") == "сегодня"
    assert reminders.deadline_label(date(2026, 10, 6), today, "ru") == "завтра"
    assert reminders.deadline_label(date(2026, 10, 8), today, "ru") == "ОКТ 08 · через 3 дн."
    assert reminders.deadline_label(date(2026, 10, 3), today, "ru") == "ОКТ 03 · просрочено на 2 дн."

    class P:
        name = "Сайт"

    class T:
        def __init__(self, title, deadline=None, position=0):
            self.title = title
            self.deadline = deadline
            self.position = position

    text = reminders.render_digest(
        [(P(), T("Черновик", date(2026, 10, 6), 0))],
        [(P(), T("Купить домен", date(2026, 10, 3), 1))],
        today,
        "ru",
    )
    assert "<b>BOARDLY // СВОДКА</b>" in text
    assert "Активные задачи: 1" in text
    assert "Черновик — завтра" in text
    assert "⚠ Просрочено: 1" in text
    assert "Купить домен [Сайт] — ОКТ 03 · просрочено на 2 дн." in text


def test_render_digest_empty_returns_none():
    assert reminders.render_digest([], [], date(2026, 10, 5)) is None


def test_render_digest_formats_sections():
    class P:
        name = "Website"

    class T:
        def __init__(self, title, deadline=None, position=0):
            self.title = title
            self.deadline = deadline
            self.position = position

    today = date(2026, 10, 5)
    active = [(P(), T("Draft copy", date(2026, 10, 6), 0))]
    deadlines = [(P(), T("Buy domain", date(2026, 10, 3), 1))]
    text = reminders.render_digest(active, deadlines, today)

    assert "<b>BOARDLY // DAILY</b>" in text
    assert "Active tasks: 1" in text
    assert "▸ Website" in text
    assert "Draft copy — due tomorrow" in text
    assert "⚠ 1 overdue" in text
    assert "Buy domain [Website] — OCT 03 · 2d overdue" in text


def test_classify_filters_backlog_stage_done_and_foreign_assignees():
    class S:
        def __init__(self, backlog=False):
            self.is_backlog = backlog

    class T:
        def __init__(self, assignee=None, deadline=None, stage_done=False):
            self.assignee_id = assignee
            self.deadline = deadline
            self.stage_done = stage_done
            self.position = 0

    class P:
        name = "p"

    me, other = "me", "other"
    today = date(2026, 10, 5)
    rows = [
        (T(me), S(backlog=True), P()),          # backlog -> not active
        (T(me), S(), P()),                       # regular stage -> active
        (T(me, stage_done=True), S(), P()),      # done sub-stage -> not active
        (T(other), S(), P()),                    # assigned to someone else -> skipped
        (T(None), S(), P()),                     # unassigned -> active
        (T(me, deadline=today), S(backlog=True), P()),  # backlog deadline still counts
    ]
    active, deadlines = reminders.classify(rows, me, today, deadline_days=2)
    assert len(active) == 2
    assert len(deadlines) == 1


# --------------------------------------------------------------------------- #
# Integration (SQLite + monkeypatched Telegram sender)
# --------------------------------------------------------------------------- #


@pytest.fixture
def reminder_env(monkeypatch):
    monkeypatch.setattr(settings, "reminders_enabled", True)
    monkeypatch.setattr(settings, "bot_token", "123:test-token")
    monkeypatch.setattr(settings, "reminders_deadline_days", 2)
    sent = []

    async def fake_send(chat_id, text):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr(reminders, "send_telegram_message", fake_send)
    return sent


def _promote_to_telegram_user(sessionmaker, user_id, telegram_id):
    async def go():
        async with sessionmaker() as db:
            user = await db.get(User, uuid.UUID(user_id))
            user.telegram_id = telegram_id
            await db.commit()

    asyncio.run(go())


def _run_daily(sessionmaker, now):
    async def go():
        async with sessionmaker() as db:
            return await reminders.process_daily(db, now)

    return asyncio.run(go())


def test_digest_sent_once_per_day(client, make_project, create_task, sessionmaker, reminder_env, stage_by_name):
    project, headers, tokens = make_project("alice")
    active = stage_by_name(project["id"], headers, "ToDo")
    backlog = stage_by_name(project["id"], headers, "Backlog")

    create_task(project["id"], headers, "In progress", stage_id=active["id"])
    create_task(project["id"], headers, "Overdue one", deadline="2026-10-03", stage_id=active["id"])
    create_task(project["id"], headers, "Backlog with deadline", deadline="2026-10-06", stage_id=backlog["id"])

    _promote_to_telegram_user(sessionmaker, tokens["user"]["id"], 555001)
    sent_count = _run_daily(sessionmaker, datetime(2026, 10, 5, 10, 0))
    assert sent_count == 1
    assert len(reminder_env) == 1
    chat_id, text = reminder_env[0]
    assert chat_id == 555001
    assert "In progress" in text
    assert "Overdue one" in text
    assert "⚠ 1 overdue" in text
    assert "Backlog with deadline [Test Project] — due tomorrow" in text

    # same day: deduplicated, no second message
    assert _run_daily(sessionmaker, datetime(2026, 10, 5, 12, 0)) == 0
    assert len(reminder_env) == 1

    # next day: sent again, and the backlog deadline is now "due today"
    assert _run_daily(sessionmaker, datetime(2026, 10, 6, 10, 0)) == 1
    assert len(reminder_env) == 2
    assert "Backlog with deadline [Test Project] — due today" in reminder_env[1][1]


def test_no_message_before_daily_time(client, make_project, create_task, sessionmaker, reminder_env, stage_by_name):
    project, headers, tokens = make_project("alice")
    active = stage_by_name(project["id"], headers, "Active")
    create_task(project["id"], headers, "Early bird", stage_id=active["id"])
    _promote_to_telegram_user(sessionmaker, tokens["user"]["id"], 555002)

    assert _run_daily(sessionmaker, datetime(2026, 10, 5, 8, 59)) == 0
    assert reminder_env == []


def test_dev_users_never_messaged(client, make_project, create_task, sessionmaker, reminder_env, stage_by_name):
    project, headers, _ = make_project("alice")  # dev users keep negative telegram ids
    active = stage_by_name(project["id"], headers, "Active")
    create_task(project["id"], headers, "Should not notify", stage_id=active["id"])

    assert _run_daily(sessionmaker, datetime(2026, 10, 5, 10, 0)) == 0
    assert reminder_env == []


def test_completed_tasks_excluded(client, make_project, create_task, sessionmaker, reminder_env):
    project, headers, tokens = make_project("alice")
    task = create_task(project["id"], headers, "Finished", deadline="2026-10-05")
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    _promote_to_telegram_user(sessionmaker, tokens["user"]["id"], 555003)

    assert _run_daily(sessionmaker, datetime(2026, 10, 5, 10, 0)) == 0
    assert reminder_env == []


def test_delivery_failure_is_retried_and_not_logged(
    client, make_project, create_task, sessionmaker, monkeypatch, stage_by_name
):
    project, headers, tokens = make_project("alice")
    active = stage_by_name(project["id"], headers, "Active")
    create_task(project["id"], headers, "Retry me", stage_id=active["id"])
    _promote_to_telegram_user(sessionmaker, tokens["user"]["id"], 555004)

    monkeypatch.setattr(settings, "reminders_enabled", True)
    monkeypatch.setattr(settings, "bot_token", "123:test-token")

    calls = []

    async def failing_send(chat_id, text):
        calls.append(chat_id)
        return False

    monkeypatch.setattr(reminders, "send_telegram_message", failing_send)

    assert _run_daily(sessionmaker, datetime(2026, 10, 5, 10, 0)) == 0
    # not logged as delivered -> the next tick retries
    assert _run_daily(sessionmaker, datetime(2026, 10, 5, 10, 30)) == 0
    assert len(calls) == 2
