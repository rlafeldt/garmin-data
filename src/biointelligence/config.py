"""Application configuration loaded from environment variables and .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Garmin
    garmin_email: str
    garmin_password: str
    garmin_token_dir: str = "~/.garminconnect"

    # Supabase
    supabase_url: str
    supabase_key: str

    # Pipeline
    target_timezone: str = "Europe/Berlin"
    log_json: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
