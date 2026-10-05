import pytest
from starlette.websockets import WebSocketDisconnect


def _ws_url(project_id: str, token: str) -> str:
    return f"/api/ws/projects/{project_id}?token={token}"


def test_ws_rejects_invalid_token(client, make_project):
    project, headers, _ = make_project()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(_ws_url(project["id"], "garbage")) as ws:
            ws.receive_json()


def test_ws_rejects_non_member(client, make_project, make_user):
    project, _, _ = make_project()
    outsider = make_user("mallory")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(_ws_url(project["id"], outsider["access_token"])) as ws:
            ws.receive_json()


def test_ws_ping_pong(client, make_project):
    project, _, tokens = make_project()
    with client.websocket_connect(_ws_url(project["id"], tokens["access_token"])) as ws:
        ws.send_text("ping")
        assert ws.receive_json() == {"type": "pong"}


def test_ws_broadcasts_task_events(client, make_project):
    project, headers, tokens = make_project()

    with client.websocket_connect(_ws_url(project["id"], tokens["access_token"])) as ws:
        task = client.post(
            f"/api/projects/{project['id']}/tasks",
            json={"title": "live"},
            headers=headers,
        ).json()

        event = ws.receive_json()
        assert event["type"] == "task.created"
        assert event["task"]["id"] == task["id"]

        client.post(f"/api/tasks/{task['id']}/complete", headers=headers)
        event = ws.receive_json()
        assert event["type"] == "tasks.reordered"
        moved = next(t for t in event["tasks"] if t["id"] == task["id"])
        assert moved["completed_at"] is not None

        client.patch(f"/api/tasks/{task['id']}", json={"title": "renamed"}, headers=headers)
        event = ws.receive_json()
        assert event["type"] == "task.updated"
        assert event["task"]["title"] == "renamed"

        client.delete(f"/api/tasks/{task['id']}", headers=headers)
        event = ws.receive_json()
        assert event["type"] == "task.deleted"
        assert event["task_id"] == task["id"]


def test_ws_broadcasts_stage_events(client, make_project, stage_by_name):
    project, headers, tokens = make_project()
    active = stage_by_name(project["id"], headers, "Active")

    with client.websocket_connect(_ws_url(project["id"], tokens["access_token"])) as ws:
        created = client.post(
            f"/api/projects/{project['id']}/stages", json={"name": "Review", "wip_limit": 2}, headers=headers
        ).json()
        event = ws.receive_json()
        assert event["type"] == "stage.created"
        assert event["stage"]["wip_limit"] == 2

        client.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=headers)
        event = ws.receive_json()
        assert event["type"] == "stage.updated"
        assert event["stage"]["is_split"] is True

        client.delete(f"/api/stages/{created['id']}", headers=headers)
        event = ws.receive_json()
        assert event["type"] == "stage.deleted"


def test_ws_broadcasts_member_events(client, make_project, make_user):
    project, headers, tokens = make_project()
    bob = make_user("bob")

    with client.websocket_connect(_ws_url(project["id"], tokens["access_token"])) as ws:
        client.post(
            f"/api/projects/{project['id']}/members", json={"user_id": bob["user"]["id"]}, headers=headers
        )
        event = ws.receive_json()
        assert event["type"] == "members.changed"
        assert any(m["user_id"] == bob["user"]["id"] for m in event["members"])
