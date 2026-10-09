"""Flow metrics per board: cycle time, time to market, CFD.

Definitions (all durations in days):
- time to market — task created → entered Done;
- cycle time     — task first left the Backlog → entered Done. Tasks whose
  start is only known from backfilled history (migration 0008) are skipped;
- CFD            — tasks per stage lane at the end of each local day.
"""

import math
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import DbDep, UserDep, get_project_with_role
from app.models import COMPLEXITY_LEVELS, Stage, Task, TaskTransition
from app.schemas import CfdBand, CfdPoint, ComplexityStats, DurationStats, MetricsOut

router = APIRouter(prefix="/api", tags=["metrics"])

MAX_DAYS = 365


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; every stored timestamp is UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _days_between(start: datetime, end: datetime) -> float:
    return max(0.0, (_as_utc(end) - _as_utc(start)).total_seconds() / 86400)


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile of a non-empty list (pct in 0..100)."""
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct / 100
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _duration_stats(values: list[float]) -> DurationStats:
    if not values:
        return DurationStats()
    return DurationStats(
        count=len(values),
        avg=round(sum(values) / len(values), 1),
        median=round(_percentile(values, 50), 1),
        p85=round(_percentile(values, 85), 1),
    )


def _cfd_bands(stages: list[Stage]) -> list[CfdBand]:
    """Bands in board order; a split stage contributes its active then done lane."""
    bands: list[CfdBand] = []
    for s in stages:
        common = {"stage_id": s.id, "name": s.name, "is_backlog": s.is_backlog, "is_done": s.is_done}
        if s.is_split:
            bands.append(CfdBand(key=f"{s.id}:active", lane="active", **common))
            bands.append(CfdBand(key=f"{s.id}:done", lane="done", **common))
        else:
            bands.append(CfdBand(key=str(s.id), **common))
    return bands


def _band_key(stages_by_id: dict[uuid.UUID, Stage], stage_id: uuid.UUID, stage_done: bool) -> str | None:
    """Band a transition lands in under the board's *current* layout (None: stage is gone)."""
    stage = stages_by_id.get(stage_id)
    if stage is None:
        return None
    if stage.is_split:
        return f"{stage.id}:{'done' if stage_done else 'active'}"
    return str(stage.id)


def _cfd_series(
    history: dict[uuid.UUID, list[tuple[datetime, str | None]]],
    day_ends: list[tuple[date, datetime]],
    band_keys: list[str],
) -> list[CfdPoint]:
    """Count each task in the band of its last transition at or before each day end.

    `history` maps a task to its (entered_at, band key) list sorted by time;
    `day_ends` is ascending.
    """
    counts = [dict.fromkeys(band_keys, 0) for _ in day_ends]
    for visits in history.values():
        cursor = -1
        for i, (_, day_end) in enumerate(day_ends):
            while cursor + 1 < len(visits) and visits[cursor + 1][0] <= day_end:
                cursor += 1
            if cursor < 0:
                continue
            key = visits[cursor][1]
            if key in counts[i]:
                counts[i][key] += 1
    return [CfdPoint(day=day, counts=c) for (day, _), c in zip(day_ends, counts)]


@router.get("/projects/{project_id}/metrics", response_model=MetricsOut)
async def get_metrics(
    project_id: uuid.UUID,
    user: UserDep,
    db: DbDep,
    days: int = Query(default=30, ge=0, le=MAX_DAYS, description="Period length; 0 = since the board was created"),
    tz_offset: int = Query(default=0, ge=-14 * 60, le=14 * 60, description="Browser getTimezoneOffset() in minutes"),
):
    project, _ = await get_project_with_role(db, user, project_id)

    stages = list(
        (await db.execute(select(Stage).where(Stage.project_id == project_id).order_by(Stage.position)))
        .scalars()
        .all()
    )
    tasks = list((await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all())
    transitions = list(
        (
            await db.execute(
                select(TaskTransition)
                .where(TaskTransition.project_id == project_id)
                .order_by(TaskTransition.entered_at)
            )
        )
        .scalars()
        .all()
    )

    # Period in the viewer's local days.
    local_tz = timezone(timedelta(minutes=-tz_offset))
    today = datetime.now(timezone.utc).astimezone(local_tz).date()
    if days == 0:
        start = _as_utc(project.created_at).astimezone(local_tz).date()
        start = max(start, today - timedelta(days=MAX_DAYS - 1))
    else:
        start = today - timedelta(days=days - 1)
    start = min(start, today)
    period_days = [start + timedelta(days=n) for n in range((today - start).days + 1)]
    day_ends = [(d, datetime.combine(d + timedelta(days=1), time.min, local_tz)) for d in period_days]
    period_from = datetime.combine(start, time.min, local_tz)

    stages_by_id = {s.id: s for s in stages}
    backlog_ids = {s.id for s in stages if s.is_backlog}
    done_ids = {s.id for s in stages if s.is_done}

    by_task: dict[uuid.UUID, list[TaskTransition]] = {}
    for tr in transitions:
        by_task.setdefault(tr.task_id, []).append(tr)

    # Lead / cycle times for tasks completed inside the period.
    cycle: dict[str, list[float]] = {level: [] for level in COMPLEXITY_LEVELS}
    ttm: dict[str, list[float]] = {level: [] for level in COMPLEXITY_LEVELS}
    completed: dict[str, int] = dict.fromkeys(COMPLEXITY_LEVELS, 0)
    for task in tasks:
        if task.stage_id not in done_ids or task.completed_at is None:
            continue
        if _as_utc(task.completed_at) < period_from:
            continue
        level = task.complexity if task.complexity in completed else "normal"
        completed[level] += 1
        ttm[level].append(_days_between(task.created_at, task.completed_at))
        started = next((tr for tr in by_task.get(task.id, []) if tr.stage_id not in backlog_ids), None)
        if started is not None and not started.backfilled:
            cycle[level].append(_days_between(started.entered_at, task.completed_at))

    wip = sum(
        1
        for t in tasks
        if t.stage_id not in backlog_ids and t.stage_id not in done_ids and not t.stage_done
    )

    bands = _cfd_bands(stages)
    history = {
        task_id: [(_as_utc(tr.entered_at), _band_key(stages_by_id, tr.stage_id, tr.stage_done)) for tr in visits]
        for task_id, visits in by_task.items()
    }

    return MetricsOut(
        project_name=project.name,
        period_start=start,
        period_end=today,
        throughput=sum(completed.values()),
        wip=wip,
        cycle_time=_duration_stats([v for values in cycle.values() for v in values]),
        time_to_market=_duration_stats([v for values in ttm.values() for v in values]),
        by_complexity=[
            ComplexityStats(
                complexity=level,
                completed=completed[level],
                cycle_time=_duration_stats(cycle[level]),
                time_to_market=_duration_stats(ttm[level]),
            )
            for level in COMPLEXITY_LEVELS
        ],
        cfd_bands=bands,
        cfd=_cfd_series(history, day_ends, [b.key for b in bands]),
    )
