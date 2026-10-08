import hashlib

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.config import settings
from app.deps import DbDep
from app.deps import UserDep
from app.models import User
from app.schemas import DevLoginIn, MiniAppAuthIn, RefreshIn, TokenPair, UserOut, UserSettingsIn, WidgetAuthIn
from app.security import create_token_pair, decode_token
from app.telegram import extract_telegram_user, verify_telegram_query

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_pair(user: User) -> TokenPair:
    access, refresh = create_token_pair(user.id)
    return TokenPair(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


async def _upsert_telegram_user(db, tg_user: dict) -> User:
    telegram_id = int(tg_user["id"])
    user = (
        await db.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()

    username = tg_user.get("username")
    first_name = tg_user.get("first_name")
    last_name = tg_user.get("last_name")
    photo_url = tg_user.get("photo_url")

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            photo_url=photo_url,
        )
        db.add(user)
    else:
        # Telegram omits fields it does not have — only overwrite what is present.
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if photo_url:
            user.photo_url = photo_url

    await db.commit()
    await db.refresh(user)
    return user


async def _login_with_telegram_payload(db, raw: str, *, webapp: bool) -> TokenPair:
    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="BOT_TOKEN is not configured")
    data = verify_telegram_query(raw, settings.bot_token, webapp=webapp)
    if data is None:
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")
    tg_user = extract_telegram_user(data)
    if tg_user is None:
        raise HTTPException(status_code=400, detail="Payload contains no user data")
    user = await _upsert_telegram_user(db, tg_user)
    return _token_pair(user)


@router.post("/telegram/widget", response_model=TokenPair)
async def widget_login(body: WidgetAuthIn, db: DbDep) -> TokenPair:
    """Exchange a Telegram Login Widget redirect payload for app tokens."""
    return await _login_with_telegram_payload(db, body.data, webapp=False)


@router.post("/telegram/miniapp", response_model=TokenPair)
async def miniapp_login(body: MiniAppAuthIn, db: DbDep) -> TokenPair:
    """Exchange Telegram Mini App `initData` for app tokens."""
    return await _login_with_telegram_payload(db, body.init_data, webapp=True)


@router.post("/dev-login", response_model=TokenPair)
async def dev_login(body: DevLoginIn, db: DbDep) -> TokenPair:
    """Development-only login used when DEV_FAKE_AUTH is enabled."""
    if not settings.dev_fake_auth:
        raise HTTPException(status_code=404, detail="Not found")
    name = body.username.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Username is required")
    # Deterministic negative id so dev users never collide with real Telegram ids.
    telegram_id = -int(hashlib.sha256(name.encode()).hexdigest()[:12], 16)
    user = (
        await db.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=name, first_name=name.capitalize())
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return _token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(body: RefreshIn, db: DbDep) -> TokenPair:
    user_id = decode_token(body.refresh_token, "refresh")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return _token_pair(user)


@router.get("/me", response_model=UserOut)
async def me(user: UserDep) -> UserOut:
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(body: UserSettingsIn, user: UserDep, db: DbDep) -> UserOut:
    """Global account settings. Language applies to the app and daily reminders."""
    user.locale = body.locale
    await db.commit()
    await db.refresh(user)
    return user
