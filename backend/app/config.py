from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Boardly"

    # PostgreSQL (async driver)
    database_url: str = "postgresql+asyncpg://boardly:boardly@db:5432/boardly"

    # JWT
    jwt_secret: str = "dev-secret-change-me"
    access_token_ttl_hours: int = 24
    refresh_token_ttl_days: int = 60

    # Telegram bot used for both the Login Widget and the Mini App
    bot_token: str = ""
    bot_username: str = ""

    # Public URL of the website (must match the domain registered in BotFather)
    app_url: str = "http://localhost:8080"

    # Development-only login without Telegram (users "alice", "bob", ...)
    dev_fake_auth: bool = True

    # Telegram reminders (daily digest of active tasks + deadlines)
    reminders_enabled: bool = True
    reminders_daily_time: str = "09:00"  # local time, HH:MM
    reminders_deadline_days: int = 2  # remind N days ahead (and when overdue)
    reminders_check_interval_min: int = 30
    reminders_timezone: str = "UTC"

    @field_validator("reminders_daily_time")
    @classmethod
    def _valid_daily_time(cls, value: str) -> str:
        try:
            hh, mm = value.strip().split(":")
            hours, minutes = int(hh), int(mm)
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
        except ValueError as exc:
            raise ValueError('reminders_daily_time must be in "HH:MM" format') from exc
        return f"{hours:02d}:{minutes:02d}"


settings = Settings()
