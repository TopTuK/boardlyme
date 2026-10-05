"""Checklists: items are appended in order, and a task can only be closed
when every item is checked. Unchecking (or adding an item) on a closed task
reopens it, so "closed => fully checked" always holds."""

import uuid


def _add_item(client, headers, task_id: str, content: str) -> dict:
    response = client.post(
        f"/api/tasks/{task_id}/checklist", json={"content": content}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["checklist"][-1]


def _patch_item(client, headers, item_id: str, **patch) -> dict:
    response = client.patch(f"/api/checklist/items/{item_id}", json=patch, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _board_task(client, headers, project_id: str, task_id: str) -> dict:
    board = client.get(f"/api/projects/{project_id}", headers=headers).json()
    return next(t for t in board["tasks"] if t["id"] == task_id)


# --------------------------------------------------------------------------- #
# Items CRUD
# --------------------------------------------------------------------------- #


def test_add_items_keeps_order(client, make_project, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")

    first = _add_item(client, headers, task["id"], "step one")
    second = _add_item(client, headers, task["id"], "step two")

    checklist = _board_task(client, headers, project["id"], task["id"])["checklist"]
    assert [i["content"] for i in checklist] == ["step one", "step two"]
    assert [i["position"] for i in checklist] == [0, 1]
    assert all(i["is_done"] is False for i in checklist)
    assert first["content"] == "step one"
    assert second["position"] == 1


def test_blank_item_rejected(client, make_project, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")

    response = client.post(
        f"/api/tasks/{task['id']}/checklist", json={"content": "   "}, headers=headers
    )
    assert response.status_code == 422


def test_toggle_and_rename_item(client, make_project, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")
    item = _add_item(client, headers, task["id"], "draft")

    body = _patch_item(client, headers, item["id"], is_done=True)
    assert body["checklist"][0]["is_done"] is True

    body = _patch_item(client, headers, item["id"], content="final")
    checklist = _board_task(client, headers, project["id"], task["id"])["checklist"]
    assert checklist[0]["content"] == "final"
    assert checklist[0]["is_done"] is True  # rename leaves the flag alone


def test_delete_item(client, make_project, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")
    item = _add_item(client, headers, task["id"], "gone")

    response = client.delete(f"/api/checklist/items/{item['id']}", headers=headers)
    assert response.status_code == 204
    assert _board_task(client, headers, project["id"], task["id"])["checklist"] == []


def test_missing_item_returns_404(client, make_project):
    project, headers, _ = make_project()

    response = client.patch(
        f"/api/checklist/items/{uuid.uuid4()}", json={"is_done": True}, headers=headers
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Closing guard
# --------------------------------------------------------------------------- #


def _task_with_checklist(client, make_project, create_task, contents, checked=()):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")
    ids = []
    for content in contents:
        ids.append(_add_item(client, headers, task["id"], content)["id"])
    for item_id in ids[:checked]:
        _patch_item(client, headers, item_id, is_done=True)
    return project, headers, task, ids


def test_complete_blocked_while_items_unchecked(client, make_project, create_task):
    project, headers, task, _ = _task_with_checklist(
        client, make_project, create_task, ["a", "b"], checked=1
    )

    response = client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "Task has unchecked checklist items"

    stored = _board_task(client, headers, project["id"], task["id"])
    assert stored["completed_at"] is None


def test_move_into_done_stage_blocked(client, make_project, create_task, stage_by_name):
    project, headers, task, _ = _task_with_checklist(
        client, make_project, create_task, ["a"], checked=0
    )
    done = stage_by_name(project["id"], headers, "Done")

    response = client.post(
        f"/api/tasks/{task['id']}/move", json={"stage_id": done["id"], "index": 0}, headers=headers
    )
    assert response.status_code == 409


def test_stage_done_sublane_not_blocked(client, make_project, create_task, stage_by_name):
    """The split-stage done sub-lane is not "closed" — the guard stays off."""
    project, headers, task, _ = _task_with_checklist(
        client, make_project, create_task, ["a"], checked=0
    )
    active = stage_by_name(project["id"], headers, "Active")
    client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)

    response = client.post(
        f"/api/tasks/{task['id']}/move",
        json={"stage_id": active["id"], "index": 0, "stage_done": True},
        headers=headers,
    )
    assert response.status_code == 200
    stored = _board_task(client, headers, project["id"], task["id"])
    assert stored["stage_done"] is True
    assert stored["completed_at"] is None


def test_complete_allowed_when_all_checked(client, make_project, create_task, board, stage_by_name):
    project, headers, task, _ = _task_with_checklist(
        client, make_project, create_task, ["a", "b"], checked=2
    )

    response = client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    assert response.status_code == 200

    done = stage_by_name(project["id"], headers, "Done")
    stored = _board_task(client, headers, project["id"], task["id"])
    assert stored["stage_id"] == done["id"]
    assert stored["completed_at"] is not None
    assert all(i["is_done"] for i in stored["checklist"])


# --------------------------------------------------------------------------- #
# Auto-reopen: closed tasks always keep a fully checked checklist
# --------------------------------------------------------------------------- #


def test_uncheck_item_reopens_completed_task(client, make_project, create_task):
    project, headers, task, ids = _task_with_checklist(
        client, make_project, create_task, ["a", "b"], checked=2
    )
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)

    body = _patch_item(client, headers, ids[0], is_done=False)
    assert body["completed_at"] is None

    stored = _board_task(client, headers, project["id"], task["id"])
    assert stored["completed_at"] is None
    # back in a work stage (Backlog is the first non-done stage)
    stages = client.get(f"/api/projects/{project['id']}", headers=headers).json()["stages"]
    backlog = next(s for s in stages if s["is_backlog"])
    assert stored["stage_id"] == backlog["id"]


def test_rename_item_keeps_task_closed(client, make_project, create_task):
    project, headers, task, ids = _task_with_checklist(
        client, make_project, create_task, ["a"], checked=1
    )
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)

    body = _patch_item(client, headers, ids[0], content="renamed")
    assert body["completed_at"] is not None


def test_delete_item_keeps_task_closed(client, make_project, create_task):
    project, headers, task, ids = _task_with_checklist(
        client, make_project, create_task, ["a"], checked=1
    )
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)

    response = client.delete(f"/api/checklist/items/{ids[0]}", headers=headers)
    assert response.status_code == 204
    stored = _board_task(client, headers, project["id"], task["id"])
    assert stored["completed_at"] is not None


def test_add_item_to_completed_task_reopens_it(client, make_project, create_task):
    project, headers, task, _ = _task_with_checklist(
        client, make_project, create_task, ["a"], checked=1
    )
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)

    body = client.post(
        f"/api/tasks/{task['id']}/checklist", json={"content": "new work"}, headers=headers
    ).json()
    assert body["completed_at"] is None
    stored = _board_task(client, headers, project["id"], task["id"])
    assert stored["completed_at"] is None
    assert len(stored["checklist"]) == 2


# --------------------------------------------------------------------------- #
# Permissions
# --------------------------------------------------------------------------- #


def test_outsider_cannot_touch_checklist(client, make_project, make_user, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")
    item = _add_item(client, headers, task["id"], "a")

    outsider = make_user("mallory")
    outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}

    assert (
        client.post(
            f"/api/tasks/{task['id']}/checklist",
            json={"content": "nope"},
            headers=outsider_headers,
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/checklist/items/{item['id']}", json={"is_done": True}, headers=outsider_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/checklist/items/{item['id']}", headers=outsider_headers).status_code
        == 403
    )
