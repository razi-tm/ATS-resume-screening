from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ATS Resume Screening API"
    environment: str = "local"
    database_url: str = "sqlite+aiosqlite:///./ats.db"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_mb: int = 15
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ATS_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
