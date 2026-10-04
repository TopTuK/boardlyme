from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["meta"])


@router.get("/api/meta")
async def meta() -> dict:
    """Public configuration consumed by the frontend."""
    return {
        "app_name": settings.app_name,
        "bot_username": settings.bot_username or None,
        "app_url": settings.app_url,
        "dev_fake_auth": settings.dev_fake_auth,
    }
