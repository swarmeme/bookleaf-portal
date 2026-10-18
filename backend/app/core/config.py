"""Application settings, loaded from environment variables / backend/.env."""

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'bookleaf.db'}"

    jwt_secret: str = "dev-only-insecure-secret-change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 8  # one working day
    # Set to true when served over HTTPS so the auth cookie is never sent in clear text.
    cookie_secure: bool = False

    gemini_api_key: str | None = None
    # Classification is a short structured task, so it runs on the cheapest model;
    # drafting needs better writing, so it gets the stronger one.
    gemini_classify_model: str = "gemini-3.5-flash-lite"
    gemini_draft_model: str = "gemini-3.8-flash"
    # Gemini 3+ models "think" before answering, which adds latency, and thinking tokens count
    # against max_output_tokens: at the default level a capped reply can come back cut off.
    # Both tasks are well specified, so keep thinking low. Empty = the model's default.
    gemini_thinking_level: str | None = "LOW"
    ai_timeout_seconds: float = 20.0
    ai_max_retries: int = 2  # retries on rate limits / server errors, with backoff
    # After repeated failures, skip AI calls for this long instead of making every
    # request wait on a dead API (a simple circuit breaker).
    ai_cooldown_seconds: int = 60

    # "Today" for business-date calculations (royalty payout windows etc.).
    as_of_date: date | None = None

    frontend_dist_dir: Path = PROJECT_DIR / "frontend" / "dist"

    @field_validator("gemini_api_key", "gemini_thinking_level", "as_of_date", mode="before")
    @classmethod
    def empty_string_is_none(cls, value):
        return value or None

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    def today(self) -> date:
        return self.as_of_date or date.today()


@lru_cache
def get_settings() -> Settings:
    return Settings()
