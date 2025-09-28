from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Falls back to SQLite (aiosqlite) if PostgreSQL credentials are not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # Runtime
    app_env: Literal["dev", "prod", "test"] = "dev"
    secret_key: str = "change-me"
    access_token_exp_minutes: int = 60
    rate_limit_login_per_min: int = 5
    rate_limit_send_per_min: int = 30

    # Database (optional for Postgres; if any missing -> use SQLite)
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None

    # Direct database URL override (useful for tests)
    database_url_env: Optional[str] = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    @property
    def database_url(self) -> str:
        if self.database_url_env:
            return self.database_url_env
        if not all([self.db_user, self.db_password, self.db_host, self.db_port, self.db_name]):
            return "sqlite+aiosqlite:///./chat_service.db"
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
