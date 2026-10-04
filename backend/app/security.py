from datetime import datetime, timedelta, timezone
import uuid

import jwt

from app.config import settings


def _create_token(user_id: uuid.UUID, token_type: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_token_pair(user_id: uuid.UUID) -> tuple[str, str]:
    access = _create_token(user_id, "access", timedelta(hours=settings.access_token_ttl_hours))
    refresh = _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_ttl_days))
    return access, refresh


def decode_token(token: str, expected_type: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    try:
        return uuid.UUID(str(payload.get("sub", "")))
    except ValueError:
        return None
