"""Shared aiogram Bot client for outgoing Telegram messages.

The app only *sends* messages (daily digests); it never consumes incoming
updates, so there is no aiogram Dispatcher here. The Bot is created lazily
from BOT_TOKEN and reused for the whole process lifetime — one HTTP session
instead of one client per call — and closed on app shutdown via close_bot().
"""

import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from app.config import settings

logger = logging.getLogger("boardly.telegram_bot")

_bot: Bot | None = None


def get_bot() -> Bot | None:
    """Return the shared Bot, creating it on first use. None when BOT_TOKEN is empty."""
    global _bot
    if _bot is None:
        if not settings.bot_token:
            return None
        _bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=AiohttpSession(timeout=15.0),
        )
    return _bot


async def close_bot() -> None:
    """Close the shared Bot's HTTP session (no-op when no bot was created)."""
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None
