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

    jwt_secret: str = "dev-only-insecure-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 8  # one working day
    # Set to true when served over HTTPS so the auth cookie is never sent in clear text.
    cookie_secure: bool = False

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # "Today" for business-date calculations (royalty payout windows etc.).
    as_of_date: date | None = None

    frontend_dist_dir: Path = PROJECT_DIR / "frontend" / "dist"

    @field_validator("gemini_api_key", "as_of_date", mode="before")
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
