import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.reminders import run_reminder_loop
from app.routers import auth, members, meta, metrics, projects, stages, tasks, ws
from app.telegram_bot import close_bot


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    reminder_task = asyncio.create_task(run_reminder_loop())
    yield
    reminder_task.cancel()
    with suppress(asyncio.CancelledError):
        await reminder_task
    await close_bot()


app = FastAPI(title="Boardly API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in [settings.app_url, "http://localhost:5173", "http://localhost:8080"] if o],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(stages.router)
app.include_router(tasks.router)
app.include_router(members.router)
app.include_router(metrics.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
