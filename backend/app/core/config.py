from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings are read from backend/.env (or real environment variables)."""

    DATABASE_URL: str  # required, e.g. postgresql+psycopg://user:pass@localhost:5432/candorify
    JWT_SECRET: str  # required, long random string
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()