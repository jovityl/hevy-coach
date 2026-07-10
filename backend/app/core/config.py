from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application config, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "hevy-coach"
    environment: str = "local"
    debug: bool = True


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so env vars are parsed once per process."""
    return Settings()
