from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chat_service.api.middleware.correlation_id import CorrelationIdMiddleware
from chat_service.api.v1.routers import (
    admin_conversations,
    conversations,
    health,
    messages,
    ws,
)
from chat_service.application.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from chat_service.config import settings
from chat_service.infrastructure.bus.redis_pubsub import RedisPubSubSubscriber

logger = logging.getLogger(__name__)


async def _on_pubsub_event(event_type: str, data: dict[str, Any]) -> None:
    """Dispatch a Redis Pub/Sub event to local WS connections."""
    from chat_service.api.v1.routers.ws import get_manager

    manager = get_manager()
    conversation_id_raw = data.get("conversation_id")
    if not conversation_id_raw:
        return

    try:
        conversation_id = UUID(conversation_id_raw)
    except ValueError:
        return

    await manager.broadcast_to_conversation(conversation_id, event_type, data)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    app.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    logger.info("Redis connection pool created")

    subscriber = RedisPubSubSubscriber(
        app.state.redis,
        settings.REDIS_PUBSUB_CHANNEL,
        _on_pubsub_event,
    )
    await subscriber.start()
    app.state.pubsub_subscriber = subscriber

    yield

    await subscriber.stop()
    await app.state.redis.aclose()
    logger.info("Redis connection pool closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LeafFlow Chat Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    _register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(conversations.router)
    app.include_router(messages.router)
    app.include_router(admin_conversations.router)
    app.include_router(ws.router)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_req: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_req: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(ConflictError)
    async def _conflict(_req: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.detail})

    @app.exception_handler(ValidationError)
    async def _validation(_req: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.detail})
