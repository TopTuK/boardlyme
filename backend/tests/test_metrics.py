import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, update

from app.models import COMPLEXITY_LEVELS, Project, Task, TaskTransition
from app.routers.metrics import _duration_stats, _percentile


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _transitions(sessionmaker, task_id: str) -> list[TaskTransition]:
    async def _load():
        async with sessionmaker() as db:
            rows = await db.execute(
                select(TaskTransition)
                .where(TaskTransition.task_id == uuid.UUID(task_id))
                .order_by(TaskTransition.entered_at)
            )
            return list(rows.scalars().all())

    return asyncio.run(_load())


def _all_transitions(sessionmaker) -> list[TaskTransition]:
    async def _load():
        async with sessionmaker() as db:
            return list((await db.execute(select(TaskTransition))).scalars().all())

    return asyncio.run(_load())


def _set_history(sessionmaker, task: dict, created_at, completed_at, visits, backfilled_from: int | None = None):
    """Rewrite a task's timestamps and replace its history with `visits`.

    visits: [(stage_id, entered_at)] in order. Rows from `backfilled_from`
    onwards are flagged as backfilled.
    """
    task_id = uuid.UUID(task["id"])

    async def _write():
        async with sessionmaker() as db:
            await db.execute(
                update(Task).where(Task.id == task_id).values(created_at=created_at, completed_at=completed_at)
            )
            await db.execute(delete(TaskTransition).where(TaskTransition.task_id == task_id))
            for i, (stage_id, at) in enumerate(visits):
                db.add(
                    TaskTransition(
                        project_id=uuid.UUID(task["project_id"]),
                        task_id=task_id,
                        stage_id=uuid.UUID(stage_id),
                        stage_done=False,
                        entered_at=at,
                        backfilled=backfilled_from is not None and i >= backfilled_from,
                    )
                )
            await db.commit()

    asyncio.run(_write())


def _set_project_created(sessionmaker, project: dict, created_at) -> None:
    async def _write():
        async with sessionmaker() as db:
            await db.execute(
                update(Project).where(Project.id == uuid.UUID(project["id"])).values(created_at=created_at)
            )
            await db.commit()

    asyncio.run(_write())


def _new_task(client, project, headers, title="t", **payload) -> dict:
    response = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": title, **payload}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Complexity
# --------------------------------------------------------------------------- #


def test_complexity_defaults_to_normal(client, make_project, board):
    project, headers, _ = make_project()
    task = _new_task(client, project, headers)
    assert task["complexity"] == "normal"
    assert board(project["id"], headers)["tasks"][0]["complexity"] == "normal"


@pytest.mark.parametrize("level", COMPLEXITY_LEVELS)
def test_complexity_accepts_every_level(client, make_project, level):
    project, headers, _ = make_project()
    task = _new_task(client, project, headers, complexity=level)
    assert task["complexity"] == level

    response = client.patch(f"/api/tasks/{task['id']}", json={"complexity": level}, headers=headers)
    assert response.status_code == 200
    assert response.json()["complexity"] == level


def test_complexity_update_and_omission(client, make_project):
    project, headers, _ = make_project()
    task = _new_task(client, project, headers)

    response = client.patch(f"/api/tasks/{task['id']}", json={"complexity": "unknown"}, headers=headers)
    assert response.json()["complexity"] == "unknown"

    # Patching other fields (or sending null) leaves the level alone.
    response = client.patch(f"/api/tasks/{task['id']}", json={"title": "renamed"}, headers=headers)
    assert response.json()["complexity"] == "unknown"
    response = client.patch(f"/api/tasks/{task['id']}", json={"complexity": None}, headers=headers)
    assert response.json()["complexity"] == "unknown"


def test_invalid_complexity_rejected(client, make_project):
    project, headers, _ = make_project()
    response = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": "x", "complexity": "huge"}, headers=headers
    )
    assert response.status_code == 422

    task = _new_task(client, project, headers)
    response = client.patch(f"/api/tasks/{task['id']}", json={"complexity": "huge"}, headers=headers)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Transition log
# --------------------------------------------------------------------------- #


def test_transitions_recorded_on_create_move_and_complete(client, make_project, stage_by_name, sessionmaker):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    todo = stage_by_name(project["id"], headers, "ToDo")
    done = stage_by_name(project["id"], headers, "Done")
    task = _new_task(client, project, headers)
    other = _new_task(client, project, headers, "other")

    rows = _transitions(sessionmaker, task["id"])
    assert [str(r.stage_id) for r in rows] == [backlog["id"]]

    # A reorder inside the same lane is not a transition.
    client.post(f"/api/tasks/{other['id']}/move", json={"stage_id": backlog["id"], "index": 0}, headers=headers)
    assert len(_transitions(sessionmaker, other["id"])) == 1

    client.post(f"/api/tasks/{task['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers)
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)

    rows = _transitions(sessionmaker, task["id"])
    assert [str(r.stage_id) for r in rows] == [backlog["id"], todo["id"], done["id"]]
    assert not any(r.backfilled for r in rows)


def test_transition_recorded_for_split_lane(client, make_project, stage_by_name, sessionmaker):
    project, headers, _ = make_project()
    active = stage_by_name(project["id"], headers, "Active")
    client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)
    task = _new_task(client, project, headers)

    client.post(f"/api/tasks/{task['id']}/move", json={"stage_id": active["id"], "index": 0}, headers=headers)
    client.post(
        f"/api/tasks/{task['id']}/move",
        json={"stage_id": active["id"], "index": 0, "stage_done": True},
        headers=headers,
    )

    rows = _transitions(sessionmaker, task["id"])
    assert [(str(r.stage_id), r.stage_done) for r in rows[1:]] == [(active["id"], False), (active["id"], True)]


def test_transition_recorded_on_checklist_reopen(client, make_project, stage_by_name, sessionmaker):
    project, headers, _ = make_project()
    task = _new_task(client, project, headers)
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)

    client.post(f"/api/tasks/{task['id']}/checklist", json={"content": "one more thing"}, headers=headers)

    rows = _transitions(sessionmaker, task["id"])
    assert len(rows) == 3
    assert str(rows[-1].stage_id) == stage_by_name(project["id"], headers, "Backlog")["id"]


def test_transitions_removed_with_task_stage_and_project(client, make_project, stage_by_name, sessionmaker):
    project, headers, _ = make_project()
    todo = stage_by_name(project["id"], headers, "ToDo")

    gone = _new_task(client, project, headers, "gone")
    client.delete(f"/api/tasks/{gone['id']}", headers=headers)
    assert _transitions(sessionmaker, gone["id"]) == []

    in_todo = _new_task(client, project, headers, "in todo")
    client.post(f"/api/tasks/{in_todo['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers)
    client.delete(f"/api/stages/{todo['id']}", headers=headers)
    assert _transitions(sessionmaker, in_todo["id"]) == []

    finished = _new_task(client, project, headers, "finished")
    client.post(f"/api/tasks/{finished['id']}/complete", headers=headers)
    assert client.delete(f"/api/projects/{project['id']}", headers=headers).status_code == 204
    assert _all_transitions(sessionmaker) == []


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def test_percentile_and_stats_helpers():
    assert _percentile([4.0], 85) == 4.0
    assert _percentile([1.0, 5.0], 50) == 3.0
    assert _percentile([5.0, 1.0], 85) == pytest.approx(4.4)
    assert _duration_stats([]).model_dump() == {"count": 0, "avg": None, "median": None, "p85": None}
    stats = _duration_stats([9.0, 3.0])
    assert (stats.count, stats.avg, stats.median, stats.p85) == (2, 6.0, 6.0, 8.1)


def test_metrics_require_membership(client, make_project, make_user):
    project, _, _ = make_project()
    stranger = make_user("mallory")
    response = client.get(
        f"/api/projects/{project['id']}/metrics",
        headers={"Authorization": f"Bearer {stranger['access_token']}"},
    )
    assert response.status_code == 403


def test_metrics_empty_board(client, make_project):
    project, headers, _ = make_project()
    response = client.get(f"/api/projects/{project['id']}/metrics", params={"days": 14}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["throughput"] == 0
    assert body["wip"] == 0
    assert body["cycle_time"]["count"] == 0
    assert body["cycle_time"]["avg"] is None
    assert len(body["cfd"]) == 14
    assert [b["name"] for b in body["cfd_bands"]] == ["Backlog", "ToDo", "Active", "Done"]
    assert [row["complexity"] for row in body["by_complexity"]] == list(COMPLEXITY_LEVELS)


def test_metrics_cycle_time_ttm_and_cfd(client, make_project, stage_by_name, sessionmaker):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    todo = stage_by_name(project["id"], headers, "ToDo")
    active = stage_by_name(project["id"], headers, "Active")
    done = stage_by_name(project["id"], headers, "Done")
    now = datetime.now(timezone.utc)
    ago = lambda days: now - timedelta(days=days)  # noqa: E731

    # Done: created 10d ago, started 6d ago, done 1d ago -> TTM 9, cycle 5.
    easy = _new_task(client, project, headers, "easy", complexity="easy")
    client.post(f"/api/tasks/{easy['id']}/complete", headers=headers)
    _set_history(
        sessionmaker, easy, ago(10), ago(1),
        [(backlog["id"], ago(10)), (todo["id"], ago(6)), (done["id"], ago(1))],
    )

    # Done: created 4d ago, started 2d ago, done 1d ago -> TTM 3, cycle 1.
    hard = _new_task(client, project, headers, "hard", complexity="difficult")
    client.post(f"/api/tasks/{hard['id']}/complete", headers=headers)
    _set_history(
        sessionmaker, hard, ago(4), ago(1),
        [(backlog["id"], ago(4)), (active["id"], ago(2)), (done["id"], ago(1))],
    )

    # In progress and waiting work (created now).
    wip = _new_task(client, project, headers, "wip")
    client.post(f"/api/tasks/{wip['id']}/move", json={"stage_id": active["id"], "index": 0}, headers=headers)
    _new_task(client, project, headers, "waiting")

    response = client.get(
        f"/api/projects/{project['id']}/metrics", params={"days": 14, "tz_offset": 0}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["throughput"] == 2
    assert body["wip"] == 1
    assert body["time_to_market"] == {"count": 2, "avg": 6.0, "median": 6.0, "p85": 8.1}
    assert body["cycle_time"] == {"count": 2, "avg": 3.0, "median": 3.0, "p85": 4.4}

    by_level = {row["complexity"]: row for row in body["by_complexity"]}
    assert by_level["easy"]["completed"] == 1
    assert by_level["easy"]["cycle_time"]["avg"] == 5.0
    assert by_level["difficult"]["time_to_market"]["avg"] == 3.0
    assert by_level["normal"]["completed"] == 0

    points = {p["day"]: p["counts"] for p in body["cfd"]}
    today = now.date()
    five_days_ago = points[(today - timedelta(days=5)).isoformat()]
    assert five_days_ago == {backlog["id"]: 0, todo["id"]: 1, active["id"]: 0, done["id"]: 0}
    latest = points[today.isoformat()]
    assert latest == {backlog["id"]: 1, todo["id"]: 0, active["id"]: 1, done["id"]: 2}

    # Both tasks were completed yesterday: a today-only period leaves them out.
    body = client.get(
        f"/api/projects/{project['id']}/metrics", params={"days": 1, "tz_offset": 0}, headers=headers
    ).json()
    assert body["period_start"] == today.isoformat()
    assert body["throughput"] == 0
    assert body["time_to_market"]["count"] == 0


def test_metrics_skip_backfilled_cycle_time(client, make_project, stage_by_name, sessionmaker):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    done = stage_by_name(project["id"], headers, "Done")
    now = datetime.now(timezone.utc)

    task = _new_task(client, project, headers)
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    _set_history(
        sessionmaker, task, now - timedelta(days=3), now - timedelta(days=1),
        [(backlog["id"], now - timedelta(days=3)), (done["id"], now - timedelta(days=1))],
        backfilled_from=0,
    )

    body = client.get(f"/api/projects/{project['id']}/metrics", headers=headers).json()
    assert body["time_to_market"]["count"] == 1
    assert body["time_to_market"]["avg"] == 2.0
    assert body["cycle_time"]["count"] == 0


def test_metrics_split_stage_bands(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    active = stage_by_name(project["id"], headers, "Active")
    client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)
    task = _new_task(client, project, headers)
    client.post(
        f"/api/tasks/{task['id']}/move",
        json={"stage_id": active["id"], "index": 0, "stage_done": True},
        headers=headers,
    )

    body = client.get(f"/api/projects/{project['id']}/metrics", params={"days": 1}, headers=headers).json()
    keys = [b["key"] for b in body["cfd_bands"]]
    assert f"{active['id']}:active" in keys and f"{active['id']}:done" in keys
    assert body["cfd"][-1]["counts"][f"{active['id']}:done"] == 1
    # A task in the done sub-lane is no longer work in progress.
    assert body["wip"] == 0


def test_metrics_report_project_name(client, make_project):
    project, headers, _ = make_project(name="Home")
    body = client.get(f"/api/projects/{project['id']}/metrics", headers=headers).json()
    assert body["project_name"] == "Home"


@pytest.mark.parametrize(
    "params",
    [{"days": -1}, {"days": 366}, {"tz_offset": 14 * 60 + 1}, {"tz_offset": -14 * 60 - 1}],
)
def test_metrics_reject_out_of_range_params(client, make_project, params):
    project, headers, _ = make_project()
    response = client.get(f"/api/projects/{project['id']}/metrics", params=params, headers=headers)
    assert response.status_code == 422


def test_metrics_all_time_starts_at_board_creation(client, make_project, sessionmaker):
    project, headers, _ = make_project()
    today = datetime.now(timezone.utc).date()
    _set_project_created(sessionmaker, project, datetime.now(timezone.utc) - timedelta(days=20))

    body = client.get(
        f"/api/projects/{project['id']}/metrics", params={"days": 0, "tz_offset": 0}, headers=headers
    ).json()

    assert body["period_start"] == (today - timedelta(days=20)).isoformat()
    assert body["period_end"] == today.isoformat()
    assert len(body["cfd"]) == 21


def test_metrics_all_time_is_capped_at_a_year(client, make_project, sessionmaker):
    project, headers, _ = make_project()
    _set_project_created(sessionmaker, project, datetime.now(timezone.utc) - timedelta(days=500))

    body = client.get(
        f"/api/projects/{project['id']}/metrics", params={"days": 0, "tz_offset": 0}, headers=headers
    ).json()

    assert len(body["cfd"]) == 365


def test_metrics_days_follow_the_viewer_time_zone(client, make_project, stage_by_name, sessionmaker):
    """A move at 23:00 UTC belongs to that UTC day, but to the next day at UTC+3."""
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    todo = stage_by_name(project["id"], headers, "ToDo")
    today = datetime.now(timezone.utc).date()
    day = today - timedelta(days=3)
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)

    task = _new_task(client, project, headers)
    client.post(f"/api/tasks/{task['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers)
    _set_history(
        sessionmaker, task, midnight - timedelta(days=2), None,
        [(backlog["id"], midnight - timedelta(days=2)), (todo["id"], midnight + timedelta(hours=23))],
    )

    def counts_on(tz_offset: int) -> dict:
        body = client.get(
            f"/api/projects/{project['id']}/metrics",
            params={"days": 14, "tz_offset": tz_offset},
            headers=headers,
        ).json()
        return next(p["counts"] for p in body["cfd"] if p["day"] == day.isoformat())

    # UTC: the move happened before the end of `day`.
    assert counts_on(0)[todo["id"]] == 1
    # UTC+3 (getTimezoneOffset() = -180): it is already 02:00 on the next day.
    at_utc_plus_3 = counts_on(-180)
    assert at_utc_plus_3[todo["id"]] == 0
    assert at_utc_plus_3[backlog["id"]] == 1


def test_metrics_reopened_task_leaves_lead_time_stats(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    todo = stage_by_name(project["id"], headers, "ToDo")
    task = _new_task(client, project, headers)
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    assert client.get(f"/api/projects/{project['id']}/metrics", headers=headers).json()["throughput"] == 1

    client.post(f"/api/tasks/{task['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers)
    body = client.get(f"/api/projects/{project['id']}/metrics", headers=headers).json()
    assert body["throughput"] == 0
    assert body["wip"] == 1
