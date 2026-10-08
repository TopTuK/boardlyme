def test_create_stage_inserts_before_done(client, make_project, board):
    project, headers, _ = make_project()
    response = client.post(f"/api/projects/{project['id']}/stages", json={"name": "Review"}, headers=headers)
    assert response.status_code == 201
    stage = response.json()
    assert stage["position"] == 3
    assert stage["is_backlog"] is False and stage["is_done"] is False

    stages = board(project["id"], headers)["stages"]
    assert [s["name"] for s in stages] == ["Backlog", "ToDo", "Active", "Review", "Done"]
    assert stages[-1]["is_done"] is True and stages[-1]["position"] == 4


def test_create_stage_with_wip_limit(client, make_project):
    project, headers, _ = make_project()
    response = client.post(
        f"/api/projects/{project['id']}/stages", json={"name": "Limited", "wip_limit": 3}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["wip_limit"] == 3


def test_wip_limit_validation_range(client, make_project):
    project, headers, _ = make_project()
    assert (
        client.post(f"/api/projects/{project['id']}/stages", json={"name": "X", "wip_limit": 0}, headers=headers).status_code
        == 422
    )
    assert (
        client.post(f"/api/projects/{project['id']}/stages", json={"name": "X", "wip_limit": 1000}, headers=headers).status_code
        == 422
    )


def test_set_and_clear_wip_limit(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    todo = stage_by_name(project["id"], headers, "ToDo")

    response = client.patch(f"/api/stages/{todo['id']}", json={"wip_limit": 5}, headers=headers)
    assert response.status_code == 200
    assert response.json()["wip_limit"] == 5

    # explicit null clears the limit
    response = client.patch(f"/api/stages/{todo['id']}", json={"wip_limit": None}, headers=headers)
    assert response.status_code == 200
    assert response.json()["wip_limit"] is None

    # omitting the field leaves it untouched
    client.patch(f"/api/stages/{todo['id']}", json={"wip_limit": 4}, headers=headers)
    response = client.patch(f"/api/stages/{todo['id']}", json={"name": "ToDo Renamed"}, headers=headers)
    assert response.json()["wip_limit"] == 4


def test_wip_limit_forbidden_on_backlog_and_done(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    done = stage_by_name(project["id"], headers, "Done")

    assert client.patch(f"/api/stages/{backlog['id']}", json={"wip_limit": 3}, headers=headers).status_code == 400
    assert client.patch(f"/api/stages/{done['id']}", json={"wip_limit": 3}, headers=headers).status_code == 400


def test_backlog_cannot_be_deleted(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    assert client.delete(f"/api/stages/{backlog['id']}", headers=headers).status_code == 400


def test_done_cannot_be_deleted(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    done = stage_by_name(project["id"], headers, "Done")
    assert client.delete(f"/api/stages/{done['id']}", headers=headers).status_code == 400


def test_cannot_delete_every_work_stage(client, make_project, board):
    """Regular work stages can all be deleted — the indestructible Backlog
    always remains a place for tasks."""
    project, headers, _ = make_project()
    client.post(f"/api/projects/{project['id']}/stages", json={"name": "Review"}, headers=headers)
    stages = board(project["id"], headers)["stages"]
    for stage in [s for s in stages if not s["is_backlog"] and not s["is_done"]]:
        assert client.delete(f"/api/stages/{stage['id']}", headers=headers).status_code == 204
    final = [s["name"] for s in board(project["id"], headers)["stages"]]
    assert final == ["Backlog", "Done"]


def test_delete_stage_removes_its_tasks(client, make_project, create_task, board, stage_by_name):
    project, headers, _ = make_project()
    stage = stage_by_name(project["id"], headers, "ToDo")
    create_task(project["id"], headers, "in doomed stage", stage_id=stage["id"])

    assert client.delete(f"/api/stages/{stage['id']}", headers=headers).status_code == 204
    tasks = board(project["id"], headers)["tasks"]
    assert all(t["stage_id"] != stage["id"] for t in tasks)


def test_reorder_stages_keeps_backlog_first(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    todo = stage_by_name(project["id"], headers, "ToDo")
    active = stage_by_name(project["id"], headers, "Active")

    response = client.put(
        f"/api/projects/{project['id']}/stages/reorder",
        json={"stage_ids": [todo["id"], backlog["id"], active["id"]]},
        headers=headers,
    )
    assert response.status_code == 400

    all_stages = board(project["id"], headers)["stages"]
    ids = [s["id"] for s in all_stages]
    response = client.put(
        f"/api/projects/{project['id']}/stages/reorder",
        json={"stage_ids": [backlog["id"], active["id"], todo["id"]] + ids[3:]},
        headers=headers,
    )
    assert response.status_code == 200
    assert [s["name"] for s in response.json()][:3] == ["Backlog", "Active", "ToDo"]


def test_reorder_rejects_non_permutation(client, make_project, board):
    project, headers, _ = make_project()
    ids = [s["id"] for s in board(project["id"], headers)["stages"]]
    response = client.put(
        f"/api/projects/{project['id']}/stages/reorder",
        json={"stage_ids": ids[:-1]},
        headers=headers,
    )
    assert response.status_code == 400


def test_reorder_stages_keeps_done_last(client, make_project, board, stage_by_name):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    todo = stage_by_name(project["id"], headers, "ToDo")
    active = stage_by_name(project["id"], headers, "Active")
    done = stage_by_name(project["id"], headers, "Done")

    response = client.put(
        f"/api/projects/{project['id']}/stages/reorder",
        json={"stage_ids": [backlog["id"], done["id"], todo["id"], active["id"]]},
        headers=headers,
    )
    assert response.status_code == 400

    # regular stages can swap freely as long as Done stays last
    response = client.put(
        f"/api/projects/{project['id']}/stages/reorder",
        json={"stage_ids": [backlog["id"], active["id"], todo["id"], done["id"]]},
        headers=headers,
    )
    assert response.status_code == 200
    assert [s["name"] for s in response.json()] == ["Backlog", "Active", "ToDo", "Done"]


def test_split_regular_stage(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    active = stage_by_name(project["id"], headers, "Active")

    response = client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["is_split"] is True


def test_split_forbidden_on_backlog_and_done(client, make_project, stage_by_name):
    project, headers, _ = make_project()
    backlog = stage_by_name(project["id"], headers, "Backlog")
    done = stage_by_name(project["id"], headers, "Done")

    assert client.patch(f"/api/stages/{backlog['id']}", json={"is_split": True}, headers=headers).status_code == 400
    assert client.patch(f"/api/stages/{done['id']}", json={"is_split": True}, headers=headers).status_code == 400


def test_unsplit_merges_lanes_and_renumbers(client, make_project, create_task, board, stage_by_name):
    project, headers, _ = make_project()
    active = stage_by_name(project["id"], headers, "Active")

    first = create_task(project["id"], headers, "first", stage_id=active["id"])
    second = create_task(project["id"], headers, "second", stage_id=active["id"])

    client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)
    # move the second task into the done sub-lane
    client.post(
        f"/api/tasks/{second['id']}/move",
        json={"stage_id": active["id"], "index": 0, "stage_done": True},
        headers=headers,
    )
    tasks = {t["id"]: t for t in board(project["id"], headers)["tasks"]}
    assert tasks[second["id"]]["stage_done"] is True
    assert tasks[first["id"]]["stage_done"] is False

    # unsplit: everything merges back into one lane, renumbered
    response = client.patch(f"/api/stages/{active['id']}", json={"is_split": False}, headers=headers)
    assert response.status_code == 200
    tasks = {t["id"]: t for t in board(project["id"], headers)["tasks"]}
    assert tasks[second["id"]]["stage_done"] is False
    assert tasks[first["id"]]["stage_done"] is False
    assert sorted(t["position"] for t in tasks.values()) == [0, 1]


def test_stage_management_requires_owner(client, make_project, make_user):
    project, headers, owner = make_project()
    bob = make_user("bob")
    bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}
    client.post(f"/api/projects/{project['id']}/members", json={"user_id": bob["user"]["id"]}, headers=headers)

    assert (
        client.post(f"/api/projects/{project['id']}/stages", json={"name": "X"}, headers=bob_headers).status_code == 403
    )
    stages = client.get(f"/api/projects/{project['id']}", headers=bob_headers).json()["stages"]
    some_stage = next(s for s in stages if not s["is_backlog"])
    assert client.patch(f"/api/stages/{some_stage['id']}", json={"name": "Y"}, headers=bob_headers).status_code == 403
