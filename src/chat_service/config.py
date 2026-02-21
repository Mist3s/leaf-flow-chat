from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 300

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = ""
    JWT_VERIFY_MODE: Literal["hs256", "jwks"] = "hs256"
    JWT_ALGORITHM: str = "HS256"
    JWKS_URL: str | None = None

    CORS_ORIGINS: list[str] = ["*"]

    OUTBOX_POLL_INTERVAL: float = 1.0
    OUTBOX_BATCH_SIZE: int = 50
    OUTBOX_MAX_ATTEMPTS: int = 5

    WS_HEARTBEAT_SECONDS: int = 30

    REDIS_PUBSUB_CHANNEL: str = "chat.fanout"

    LEAF_EVENTS_STREAM: str = "leaf.events"
    LEAF_EVENTS_GROUP: str = "chat-service"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg2")

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
