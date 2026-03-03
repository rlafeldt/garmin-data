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

    # Health Profile
    health_profile_path: str = "health_profile.yaml"

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-haiku-4-5-20250514"

    # Resend (delivery)
    resend_api_key: str = ""
    sender_email: str = ""
    recipient_email: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
