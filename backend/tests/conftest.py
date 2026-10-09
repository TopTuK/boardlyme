"""Shared fixtures: a throwaway SQLite database + a Starlette test client.

The app's Postgres engine is created at import time but never connected here —
`get_db` is overridden and the WebSocket router's SessionLocal is patched to
point at the test database, so every request runs against isolated storage.
"""

import asyncio

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.models import Base, ChecklistItem, Project, ProjectMember, Stage, Task, TaskTransition, User


async def _create_all(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _dispose(engine) -> None:
    await engine.dispose()


async def _truncate(sessionmaker) -> None:
    async with sessionmaker() as db:
        for model in (ChecklistItem, TaskTransition, Task, Stage, ProjectMember, Project, User):
            await db.execute(delete(model))
        await db.commit()


@pytest.fixture(scope="session")
def sessionmaker(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("boardly-tests") / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", poolclass=NullPool)
    asyncio.run(_create_all(engine))
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    asyncio.run(_dispose(engine))


@pytest.fixture(autouse=True)
def clean_database(sessionmaker):
    asyncio.run(_truncate(sessionmaker))
    yield


@pytest.fixture
def client(sessionmaker, monkeypatch):
    from app.main import app
    import app.routers.ws as ws_router

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(ws_router, "SessionLocal", sessionmaker)
    monkeypatch.setattr(settings, "dev_fake_auth", True)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


@pytest.fixture
def make_user(client):
    def _make(username: str) -> dict:
        response = client.post("/api/auth/dev-login", json={"username": username})
        assert response.status_code == 200, response.text
        return response.json()

    return _make


@pytest.fixture
def make_project(client, make_user):
    def _make(username: str = "alice", name: str = "Test Project"):
        tokens = make_user(username)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post("/api/projects", json={"name": name}, headers=headers)
        assert response.status_code == 201, response.text
        return response.json(), headers, tokens

    return _make


@pytest.fixture
def board(client):
    def _board(project_id: str, headers: dict) -> dict:
        response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert response.status_code == 200, response.text
        return response.json()

    return _board


@pytest.fixture
def stage_by_name(board):
    def _stage(project_id: str, headers: dict, name: str) -> dict:
        return next(s for s in board(project_id, headers)["stages"] if s["name"] == name)

    return _stage


@pytest.fixture
def create_task(client):
    def _create(project_id: str, headers: dict, title: str, **payload) -> dict:
        # Creation is Backlog-only. A requested stage is reached with a move,
        # which is how the board itself places work.
        stage_id = payload.pop("stage_id", None)
        stage_done = bool(payload.pop("stage_done", False))
        response = client.post(
            f"/api/projects/{project_id}/tasks",
            json={"title": title, **payload},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        task = response.json()
        if stage_id is not None and (str(stage_id) != str(task["stage_id"]) or stage_done):
            moved = client.post(
                f"/api/tasks/{task['id']}/move",
                json={"stage_id": stage_id, "index": 10**9, "stage_done": stage_done},
                headers=headers,
            )
            assert moved.status_code == 200, moved.text
            task = next(t for t in moved.json()["tasks"] if t["id"] == task["id"])
        return task

    return _create
