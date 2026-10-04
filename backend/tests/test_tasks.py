def test_new_task_defaults_to_backlog(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    response = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "fresh"}, headers=headers)
    assert response.status_code == 201
    backlog = stage_by_name(project["id"], headers, "Backlog")
    assert response.json()["stage_id"] == backlog["id"]
    assert response.json()["stage_done"] is False


def test_create_task_in_explicit_stage(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    todo = stage_by_name(project["id"], headers, "ToDo")
    task = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": "x", "stage_id": todo["id"]}, headers=headers
    ).json()
    assert task["stage_id"] == todo["id"]


def test_create_task_in_foreign_stage_rejected(client, make_project):
    project_a, headers_a, _ = make_project("alice", "A")
    project_b, headers_b, _ = make_project("bob", "B")
    stages_b = client.get(f"/api/projects/{project_b['id']}", headers=headers_b).json()["stages"]
    response = client.post(
        f"/api/projects/{project_a['id']}/tasks",
        json={"title": "x", "stage_id": stages_b[0]["id"]},
        headers=headers_a,
    )
    assert response.status_code == 400


def test_update_task_fields(client, make_project):
    project, headers, _ = make_project()
    task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "old"}, headers=headers).json()

    response = client.patch(
        f"/api/tasks/{task['id']}",
        json={"title": "new", "description": "desc", "deadline": "2030-05-01"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "new"
    assert body["description"] == "desc"
    assert body["deadline"] == "2030-05-01"

    # clear the deadline with an explicit null
    response = client.patch(f"/api/tasks/{task['id']}", json={"deadline": None}, headers=headers)
    assert response.json()["deadline"] is None


def test_move_task_between_stages(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "x"}, headers=headers).json()
    active = stage_by_name(project["id"], headers, "Active")

    response = client.post(
        f"/api/tasks/{task['id']}/move", json={"stage_id": active["id"], "index": 0}, headers=headers
    )
    assert response.status_code == 200
    moved = next(t for t in response.json()["tasks"] if t["id"] == task["id"])
    assert moved["stage_id"] == active["id"]
    assert moved["position"] == 0


def test_move_task_reorders_within_lane(client, make_project, board):
    project, headers, _ = make_project()
    stages = board(project["id"], headers)["stages"]
    backlog = next(s for s in stages if s["is_backlog"])
    a = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "a"}, headers=headers).json()
    b = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "b"}, headers=headers).json()

    response = client.post(
        f"/api/tasks/{a['id']}/move", json={"stage_id": backlog["id"], "index": 1}, headers=headers
    )
    assert response.status_code == 200
    tasks = {t["id"]: t for t in response.json()["tasks"]}
    assert tasks[a["id"]]["position"] == 1
    assert tasks[b["id"]]["position"] == 0


def test_complete_moves_to_done_stage(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "x"}, headers=headers).json()

    response = client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    assert response.status_code == 200
    done = stage_by_name(project["id"], headers, "Done")
    tasks = {t["id"]: t for t in board(project["id"], headers)["tasks"]}
    assert tasks[task["id"]]["stage_id"] == done["id"]
    assert tasks[task["id"]]["completed_at"] is not None
    assert tasks[task["id"]]["stage_done"] is False


def test_reopen_clears_completed_at(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "x"}, headers=headers).json()
    client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
    backlog = stage_by_name(project["id"], headers, "Backlog")

    response = client.post(
        f"/api/tasks/{task['id']}/move", json={"stage_id": backlog["id"], "index": 0}, headers=headers
    )
    assert response.status_code == 200
    moved = next(t for t in response.json()["tasks"] if t["id"] == task["id"])
    assert moved["completed_at"] is None
    assert moved["stage_id"] == backlog["id"]


# --------------------------------------------------------------------------- #
# Sub-stages (active / done lanes)
# --------------------------------------------------------------------------- #


def test_move_into_done_substage(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    active = stage_by_name(project["id"], headers, "Active")
    client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)
    task = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": "x", "stage_id": active["id"]}, headers=headers
    ).json()

    response = client.post(
        f"/api/tasks/{task['id']}/move",
        json={"stage_id": active["id"], "index": 0, "stage_done": True},
        headers=headers,
    )
    assert response.status_code == 200
    moved = next(t for t in response.json()["tasks"] if t["id"] == task["id"])
    assert moved["stage_done"] is True
    assert moved["completed_at"] is None  # sub-stage done is not global completion


def test_create_task_directly_into_done_substage(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    active = stage_by_name(project["id"], headers, "Active")
    client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)

    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"title": "x", "stage_id": active["id"], "stage_done": True},
        headers=headers,
    ).json()
    assert task["stage_done"] is True


# --------------------------------------------------------------------------- #
# WIP limits
# --------------------------------------------------------------------------- #


def _limited_stage(client, make_project, stage_by_name, limit=2):
    project, headers, _ = make_project()
    todo = stage_by_name(project["id"], headers, "ToDo")
    client.patch(f"/api/stages/{todo['id']}", json={"wip_limit": limit}, headers=headers)
    return project, headers, todo


def test_wip_limit_blocks_task_creation(client, make_project, stage_by_name):
    project, headers, todo = _limited_stage(client, make_project, stage_by_name, limit=2)
    for i in range(2):
        response = client.post(
            f"/api/projects/{project['id']}/tasks", json={"title": f"t{i}", "stage_id": todo["id"]}, headers=headers
        )
        assert response.status_code == 201
    response = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": "overflow", "stage_id": todo["id"]}, headers=headers
    )
    assert response.status_code == 409
    assert "WIP" in response.json()["detail"]


def test_wip_limit_blocks_move_in(client, make_project, create_task, stage_by_name):
    project, headers, todo = _limited_stage(client, make_project, stage_by_name, limit=1)
    create_task(project["id"], headers, "filler", stage_id=todo["id"])
    backlog_task = create_task(project["id"], headers, "wants in")  # lands in Backlog

    response = client.post(
        f"/api/tasks/{backlog_task['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers
    )
    assert response.status_code == 409


def test_wip_limit_ignores_done_substage(client, make_project, create_task, stage_by_name):
    project, headers, todo = _limited_stage(client, make_project, stage_by_name, limit=1)
    first = create_task(project["id"], headers, "first", stage_id=todo["id"])
    client.patch(f"/api/stages/{todo['id']}", json={"is_split": True}, headers=headers)

    # active lane is full, but the done sub-lane is not limited
    response = client.post(
        f"/api/tasks/{first['id']}/move",
        json={"stage_id": todo["id"], "index": 0, "stage_done": True},
        headers=headers,
    )
    assert response.status_code == 200

    # now the active lane has room again
    backlog_task = create_task(project["id"], headers, "next")
    response = client.post(
        f"/api/tasks/{backlog_task['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers
    )
    assert response.status_code == 200

    # ...and moving back into the full active lane is refused
    response = client.post(
        f"/api/tasks/{first['id']}/move",
        json={"stage_id": todo["id"], "index": 0, "stage_done": False},
        headers=headers,
    )
    assert response.status_code == 409


def test_wip_limit_allows_reordering_within_full_lane(client, make_project, create_task, stage_by_name):
    project, headers, todo = _limited_stage(client, make_project, stage_by_name, limit=2)
    a = create_task(project["id"], headers, "a", stage_id=todo["id"])
    b = create_task(project["id"], headers, "b", stage_id=todo["id"])

    response = client.post(
        f"/api/tasks/{a['id']}/move", json={"stage_id": todo["id"], "index": 1}, headers=headers
    )
    assert response.status_code == 200
    tasks = {t["id"]: t for t in response.json()["tasks"]}
    assert tasks[a["id"]]["position"] == 1
    assert tasks[b["id"]]["position"] == 0


def test_wip_limit_frees_slot_when_task_moves_out(client, make_project, create_task, stage_by_name):
    project, headers, todo = _limited_stage(client, make_project, stage_by_name, limit=1)
    fill = create_task(project["id"], headers, "fill", stage_id=todo["id"])
    other = create_task(project["id"], headers, "other")

    blocked = client.post(
        f"/api/tasks/{other['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers
    )
    assert blocked.status_code == 409

    active = stage_by_name(project["id"], headers, "Active")
    client.post(f"/api/tasks/{fill['id']}/move", json={"stage_id": active["id"], "index": 0}, headers=headers)

    response = client.post(
        f"/api/tasks/{other['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=headers
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Assignment & permissions
# --------------------------------------------------------------------------- #


def test_assignee_must_be_member(client, make_project, make_user, create_task):
    project, headers, _ = make_project()
    stranger = make_user("stranger")
    task = create_task(project["id"], headers, "x")

    response = client.patch(
        f"/api/tasks/{task['id']}", json={"assignee_id": stranger["user"]["id"]}, headers=headers
    )
    assert response.status_code == 400


def test_assign_member_to_task(client, make_project, make_user, create_task):
    project, headers, _ = make_project()
    bob = make_user("bob")
    client.post(f"/api/projects/{project['id']}/members", json={"user_id": bob["user"]["id"]}, headers=headers)
    task = create_task(project["id"], headers, "x")

    response = client.patch(
        f"/api/tasks/{task['id']}", json={"assignee_id": bob["user"]["id"]}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["assignee"]["id"] == bob["user"]["id"]

    # removing the member detaches their tasks
    client.delete(f"/api/projects/{project['id']}/members/{bob['user']['id']}", headers=headers)
    board = client.get(f"/api/projects/{project['id']}", headers=headers).json()
    task_now = next(t for t in board["tasks"] if t["id"] == task["id"])
    assert task_now["assignee_id"] is None


def test_outsider_cannot_touch_tasks(client, make_project, make_user, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")
    outsider = make_user("mallory")
    outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}

    assert (
        client.patch(f"/api/tasks/{task['id']}", json={"title": "nope"}, headers=outsider_headers).status_code == 403
    )
    assert client.post(f"/api/tasks/{task['id']}/complete", headers=outsider_headers).status_code == 403
    assert client.delete(f"/api/tasks/{task['id']}", headers=outsider_headers).status_code == 403


def test_delete_task(client, make_project, create_task):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "x")
    assert client.delete(f"/api/tasks/{task['id']}", headers=headers).status_code == 204
    board = client.get(f"/api/projects/{project['id']}", headers=headers).json()
    assert all(t["id"] != task["id"] for t in board["tasks"])
