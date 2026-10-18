from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_PLACEHOLDERS = {"", "change-me", "REPLACE_WITH_RANDOM_STRING", "your-generated-secret"}


class Settings(BaseSettings):
    """Settings are read from backend/.env locally, or from the host's environment variables in production.
    See docs/SETUP.md for the full list and safe defaults."""

    ENV: Literal["development", "production"] = "development"

    DATABASE_URL: str  # required, e.g. postgresql+psycopg://user:pass@host:5432/candorify
    JWT_SECRET: str  # required, long random string (at least 32 characters in production)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Only these frontend origins may call the API from a browser / the Tauri window.
    CORS_ORIGINS: list[str] = [
        "http://localhost:1420",   # Tauri dev server
        "tauri://localhost",       # Tauri app on Mac/Linux
        "http://tauri.localhost",  # Tauri app on Windows
    ]

    # Retention: stored bills are deleted automatically this many days after upload.
    RETENTION_DAYS: int = 30
    RETENTION_SWEEP_MINUTES: int = 60  # how often the automatic sweep runs (0 = never; run the script instead)

    # Interactive API docs at /docs. Default: on in development, off in production.
    DOCS_ENABLED: bool | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_psycopg_driver(cls, v: str) -> str:
        # Hosts (Render, Neon, Heroku...) hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver name.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @model_validator(mode="after")
    def _safe_production_settings(self):
        if self.RETENTION_DAYS < 1:
            raise ValueError("RETENTION_DAYS must be at least 1")
        if self.ENV == "production":
            if self.JWT_SECRET in DEV_SECRET_PLACEHOLDERS or len(self.JWT_SECRET) < 32:
                raise ValueError("In production JWT_SECRET must be a random string of at least 32 characters")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("In production DATABASE_URL must point to PostgreSQL (SQLite data is lost on redeploy)")
            if any(o == "*" for o in self.CORS_ORIGINS):
                raise ValueError("In production CORS_ORIGINS must list the real frontend origins, not '*'")
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.DOCS_ENABLED if self.DOCS_ENABLED is not None else self.ENV != "production"


settings = Settings()