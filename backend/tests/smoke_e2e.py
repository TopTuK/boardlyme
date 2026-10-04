"""End-to-end smoke test against a running Boardly stack (default: http://localhost:8080).

Usage:  .venv/Scripts/python.exe tests/smoke_e2e.py [base_url]
"""

import sys
import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
FAILED = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILED.append(name)


def client():
    return httpx.Client(base_url=BASE, timeout=10)


def login(c, username):
    r = c.post("/api/auth/dev-login", json={"username": username})
    assert r.status_code == 200, r.text
    return r.json()


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    c = client()

    # --- meta & health ---
    meta = c.get("/api/meta").json()
    check("meta endpoint", meta["app_name"] == "Boardly")
    check("health endpoint", c.get("/api/health").json()["status"] == "ok")

    # --- auth: two dev users ---
    alice = login(c, "alice")
    bob = login(c, "bob")
    check("dev login alice", alice["user"]["username"] == "alice")
    check("dev login bob", bob["user"]["username"] == "bob")

    me = c.get("/api/auth/me", headers=auth_header(alice["access_token"]))
    check("GET /auth/me", me.status_code == 200 and me.json()["id"] == alice["user"]["id"])

    refreshed = c.post("/api/auth/refresh", json={"refresh_token": alice["refresh_token"]})
    check("token refresh", refreshed.status_code == 200 and "access_token" in refreshed.json())

    check("unauthenticated request rejected", c.get("/api/projects").status_code == 401)

    # --- project creation with default stages ---
    r = c.post("/api/projects", json={"name": "Smoke Project"}, headers=auth_header(alice["access_token"]))
    check("create project", r.status_code == 201, r.text)
    project = r.json()
    pid = project["id"]
    check("project role is owner", project["role"] == "owner")

    board = c.get(f"/api/projects/{pid}", headers=auth_header(alice["access_token"])).json()
    names = [s["name"] for s in board["stages"]]
    check("default stages", names == ["Backlog", "ToDo", "Active", "Done"], str(names))
    backlog = next(s for s in board["stages"] if s["is_backlog"])
    check("backlog is first and flagged", backlog["position"] == 0 and backlog["is_backlog"] is True)
    done = next(s for s in board["stages"] if s["is_done"])
    check("done stage hidden by default", done["is_hidden"] is True)
    check("single member (owner)", len(board["members"]) == 1 and board["members"][0]["role"] == "owner")

    todo = next(s for s in board["stages"] if s["name"] == "ToDo")
    active = next(s for s in board["stages"] if s["name"] == "Active")

    # --- tasks ---
    r = c.post(f"/api/projects/{pid}/tasks", json={"title": "First task"}, headers=auth_header(alice["access_token"]))
    check("create task (defaults to Backlog)", r.status_code == 201 and r.json()["stage_id"] == backlog["id"], r.text)
    t1 = r.json()

    r = c.post(
        f"/api/projects/{pid}/tasks",
        json={"title": "Second task", "description": "with description", "deadline": "2030-01-01"},
        headers=auth_header(alice["access_token"]),
    )
    t2 = r.json()

    r = c.patch(f"/api/tasks/{t1['id']}", json={"title": "First task (edited)"}, headers=auth_header(alice["access_token"]))
    check("update task", r.status_code == 200 and r.json()["title"] == "First task (edited)")

    # --- move & complete ---
    r = c.post(f"/api/tasks/{t1['id']}/move", json={"stage_id": active["id"], "index": 0}, headers=auth_header(alice["access_token"]))
    check("move task", r.status_code == 200 and any(t["id"] == t1["id"] and t["stage_id"] == active["id"] for t in r.json()["tasks"]))

    r = c.post(f"/api/tasks/{t2['id']}/complete", headers=auth_header(alice["access_token"]))
    check("complete task", r.status_code == 200)
    board = c.get(f"/api/projects/{pid}", headers=auth_header(alice["access_token"])).json()
    t2_now = next(t for t in board["tasks"] if t["id"] == t2["id"])
    check("completed task in Done stage", t2_now["stage_id"] == done["id"] and t2_now["completed_at"])

    r = c.post(f"/api/tasks/{t2['id']}/move", json={"stage_id": todo["id"], "index": 0}, headers=auth_header(alice["access_token"]))
    t2_now = next(t for t in r.json()["tasks"] if t["id"] == t2["id"])
    check("reopen clears completed_at", t2_now["completed_at"] is None)

    # --- WIP limits ---
    c.patch(f"/api/stages/{todo['id']}", json={"wip_limit": 1}, headers=auth_header(alice["access_token"]))
    r = c.post(f"/api/projects/{pid}/tasks", json={"title": "Over limit", "stage_id": todo["id"]}, headers=auth_header(alice["access_token"]))
    check("WIP limit blocks overflow", r.status_code == 409)
    c.patch(f"/api/stages/{todo['id']}", json={"wip_limit": None}, headers=auth_header(alice["access_token"]))

    # --- sub-stages ---
    c.patch(f"/api/stages/{active['id']}", json={"is_split": True}, headers=auth_header(alice["access_token"]))
    r = c.post(f"/api/tasks/{t1['id']}/move", json={"stage_id": active["id"], "index": 0, "stage_done": True}, headers=auth_header(alice["access_token"]))
    t1_now = next(t for t in r.json()["tasks"] if t["id"] == t1["id"])
    check("move into done sub-stage", t1_now["stage_done"] is True and t1_now["completed_at"] is None)
    r = c.patch(f"/api/stages/{active['id']}", json={"is_split": False}, headers=auth_header(alice["access_token"]))
    check("merge sub-stages", r.status_code == 200 and r.json()["is_split"] is False)
    board = c.get(f"/api/projects/{pid}", headers=auth_header(alice["access_token"])).json()
    t1_now = next(t for t in board["tasks"] if t["id"] == t1["id"])
    check("merge resets stage_done", t1_now["stage_done"] is False)

    # --- sharing ---
    check("bob cannot see alice's board", c.get(f"/api/projects/{pid}", headers=auth_header(bob["access_token"])).status_code == 403)

    r = c.get(f"/api/projects/{pid}/members/search", params={"q": "bo"}, headers=auth_header(alice["access_token"]))
    check("member search", r.status_code == 200 and any(u["id"] == bob["user"]["id"] and not u["is_member"] for u in r.json()))

    r = c.post(f"/api/projects/{pid}/members", json={"user_id": bob["user"]["id"]}, headers=auth_header(alice["access_token"]))
    check("add member", r.status_code == 201 and any(m["user_id"] == bob["user"]["id"] for m in r.json()))

    check("bob sees shared board", c.get(f"/api/projects/{pid}", headers=auth_header(bob["access_token"])).status_code == 200)

    # bob (editor) can create & self-assign a task
    r = c.post(
        f"/api/projects/{pid}/tasks",
        json={"title": "Bob's task", "assignee_id": bob["user"]["id"]},
        headers=auth_header(bob["access_token"]),
    )
    check("editor creates task", r.status_code == 201 and r.json()["assignee"]["id"] == bob["user"]["id"], r.text)
    t3 = r.json()

    # permissions: bob cannot manage members / stages / project
    check("editor cannot share", c.post(f"/api/projects/{pid}/members", json={"user_id": bob["user"]["id"]}, headers=auth_header(bob["access_token"])).status_code == 403)
    check("editor cannot add stage", c.post(f"/api/projects/{pid}/stages", json={"name": "X"}, headers=auth_header(bob["access_token"])).status_code == 403)
    check("editor cannot rename project", c.patch(f"/api/projects/{pid}", json={"name": "Nope"}, headers=auth_header(bob["access_token"])).status_code == 403)

    # assignee must be a member
    r = c.patch(f"/api/tasks/{t1['id']}", json={"assignee_id": alice["user"]["id"]}, headers=auth_header(bob["access_token"]))
    check("editor assigns alice", r.status_code == 200 and r.json()["assignee_id"] == alice["user"]["id"])

    # --- stages ---
    r = c.post(f"/api/projects/{pid}/stages", json={"name": "Review"}, headers=auth_header(alice["access_token"]))
    check("add stage", r.status_code == 201 and r.json()["position"] == 4)
    review = r.json()

    r = c.put(
        f"/api/projects/{pid}/stages/reorder",
        json={"stage_ids": [backlog["id"], todo["id"], review["id"], active["id"], done["id"]]},
        headers=auth_header(alice["access_token"]),
    )
    check(
        "reorder stages",
        r.status_code == 200 and [s["name"] for s in r.json()] == ["Backlog", "ToDo", "Review", "Active", "Done"],
    )

    r = c.put(
        f"/api/projects/{pid}/stages/reorder",
        json={"stage_ids": [todo["id"], backlog["id"], review["id"], active["id"], done["id"]]},
        headers=auth_header(alice["access_token"]),
    )
    check("backlog must stay first", r.status_code == 400)

    r = c.patch(f"/api/stages/{done['id']}", json={"is_hidden": False}, headers=auth_header(alice["access_token"]))
    check("unhide done stage", r.status_code == 200 and r.json()["is_hidden"] is False)

    check("cannot delete done stage", c.delete(f"/api/stages/{done['id']}", headers=auth_header(alice["access_token"])).status_code == 400)

    r = c.delete(f"/api/stages/{review['id']}", headers=auth_header(alice["access_token"]))
    check("delete empty stage", r.status_code == 204)

    # --- delete task, remove member, leave ---
    check("delete task", c.delete(f"/api/tasks/{t3['id']}", headers=auth_header(bob["access_token"])).status_code == 204)
    check(
        "remove member",
        c.delete(f"/api/projects/{pid}/members/{bob['user']['id']}", headers=auth_header(alice["access_token"])).status_code == 204,
    )
    check("bob lost access", c.get(f"/api/projects/{pid}", headers=auth_header(bob["access_token"])).status_code == 403)

    # --- project list & cleanup ---
    listing = c.get("/api/projects", headers=auth_header(alice["access_token"])).json()
    check("project list with counts", any(p["id"] == pid and p["task_count"] >= 2 for p in listing))

    check("delete project", c.delete(f"/api/projects/{pid}", headers=auth_header(alice["access_token"])).status_code == 204)
    check("project gone", c.get(f"/api/projects/{pid}", headers=auth_header(alice["access_token"])).status_code == 404)

    # --- frontend served ---
    page = c.get("/")
    check("frontend served", page.status_code == 200 and 'id="app"' in page.text)

    print()
    if FAILED:
        print(f"SMOKE FAILED: {len(FAILED)} check(s): {FAILED}")
        sys.exit(1)
    print("SMOKE OK — all checks passed")


if __name__ == "__main__":
    main()
