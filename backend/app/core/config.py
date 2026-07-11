from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/  (three levels up from this file)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Typed application config, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "hevy-coach"
    environment: str = "local"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://hevy:hevy@localhost:5433/hevy"

    # Supabase Auth — set from Project Settings -> API once the project exists.
    supabase_url: str = "REPLACE_ME"
    supabase_anon_key: str = "REPLACE_ME"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so env vars are parsed once per process."""
    return Settings()
