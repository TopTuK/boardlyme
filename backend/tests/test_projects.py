DEFAULT_STAGE_NAMES = ["Backlog", "ToDo", "Active", "Done"]


def test_create_project_builds_default_stages(make_project, board):
    project, headers, _ = make_project()
    stages = board(project["id"], headers)["stages"]
    assert [s["name"] for s in stages] == DEFAULT_STAGE_NAMES

    backlog = stages[0]
    assert backlog["is_backlog"] is True
    assert backlog["position"] == 0
    assert backlog["wip_limit"] is None
    assert backlog["is_split"] is False

    done = stages[3]
    assert done["is_done"] is True
    assert done["is_hidden"] is True


def test_create_project_requires_auth(client):
    assert client.post("/api/projects", json={"name": "X"}).status_code == 401


def test_create_project_validates_name(client, make_project):
    _, headers, _ = make_project()
    assert client.post("/api/projects", json={"name": "  "}, headers=headers).status_code == 422
    assert client.post("/api/projects", json={"name": ""}, headers=headers).status_code == 422


def test_owner_is_created_as_member(make_project, board):
    project, headers, tokens = make_project()
    members = board(project["id"], headers)["members"]
    assert len(members) == 1
    assert members[0]["role"] == "owner"
    assert members[0]["user_id"] == tokens["user"]["id"]


def test_list_projects_returns_only_membership(client, make_project, make_user):
    project_a, headers_a, _ = make_project("alice", "Alpha")
    project_b, headers_b, _ = make_project("bob", "Beta")

    listing = client.get("/api/projects", headers=headers_a).json()
    ids = [p["id"] for p in listing]
    assert project_a["id"] in ids
    assert project_b["id"] not in ids

    # after sharing, bob sees both
    bob = make_user("bob")
    client.post(
        f"/api/projects/{project_a['id']}/members",
        json={"user_id": bob["user"]["id"]},
        headers=headers_a,
    )
    listing = client.get("/api/projects", headers=headers_b).json()
    ids = [p["id"] for p in listing]
    assert project_b["id"] in ids
    assert project_a["id"] in ids


def test_list_projects_counts_tasks(client, make_project, create_task):
    project, headers, _ = make_project()
    create_task(project["id"], headers, "one")
    create_task(project["id"], headers, "two")
    create_task(project["id"], headers, "three")

    listing = client.get("/api/projects", headers=headers).json()
    mine = next(p for p in listing if p["id"] == project["id"])
    assert mine["task_count"] == 3
    assert mine["done_count"] == 0


def test_rename_project_owner_only(client, make_project, make_user):
    project, headers, _ = make_project()
    outsider = make_user("mallory")
    outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}

    response = client.patch(f"/api/projects/{project['id']}", json={"name": "Hacked"}, headers=outsider_headers)
    assert response.status_code == 403

    response = client.patch(f"/api/projects/{project['id']}", json={"name": "Renamed"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_delete_project_owner_only(client, make_project, make_user):
    project, headers, _ = make_project()
    outsider = make_user("mallory")
    outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}

    assert client.delete(f"/api/projects/{project['id']}", headers=outsider_headers).status_code == 403
    assert client.delete(f"/api/projects/{project['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/projects/{project['id']}", headers=headers).status_code == 404


def test_delete_project_cascades_stages_and_tasks(client, make_project, create_task, board):
    project, headers, _ = make_project()
    task = create_task(project["id"], headers, "doomed")
    assert client.delete(f"/api/projects/{project['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/tasks/{task['id']}", headers=headers).status_code in (404, 405)


def test_leave_project_as_editor(client, make_project, make_user):
    project, headers, owner_tokens = make_project()
    bob = make_user("bob")
    bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}
    client.post(f"/api/projects/{project['id']}/members", json={"user_id": bob["user"]["id"]}, headers=headers)

    assert client.post(f"/api/projects/{project['id']}/leave", headers=bob_headers).status_code == 204
    assert client.get(f"/api/projects/{project['id']}", headers=bob_headers).status_code == 403
    # owner still sees the board
    assert client.get(f"/api/projects/{project['id']}", headers=headers).status_code == 200


def test_owner_cannot_leave(client, make_project):
    project, headers, _ = make_project()
    assert client.post(f"/api/projects/{project['id']}/leave", headers=headers).status_code == 400


def test_get_board_denied_for_non_member(client, make_project, make_user):
    project, headers, _ = make_project()
    outsider = make_user("mallory")
    outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}
    assert client.get(f"/api/projects/{project['id']}", headers=outsider_headers).status_code == 403
