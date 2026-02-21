"""Redis Pub/Sub — publish side + subscriber background task."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

import redis.asyncio as aioredis

from chat_service.infrastructure.bus.serializer import deserialize_event, serialize_event

logger = logging.getLogger(__name__)


class RedisPubSubPublisher:
    """Implements application.ports.bus.EventPublisher."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        raw = serialize_event(payload.get("event_type", "unknown"), payload)
        await self._redis.publish(channel, raw)


OnEventCallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class RedisPubSubSubscriber:
    """Background task that listens to a Redis channel and dispatches events."""

    def __init__(
        self,
        redis: aioredis.Redis,
        channel: str,
        callback: OnEventCallback,
    ) -> None:
        self._redis = redis
        self._channel = channel
        self._callback = callback
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._listen(), name="redis-pubsub-subscriber")
        logger.info("Redis Pub/Sub subscriber started on channel=%s", self._channel)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Redis Pub/Sub subscriber stopped")

    async def _listen(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event_type, data = deserialize_event(message["data"])
                    await self._callback(event_type, data)
                except Exception:
                    logger.exception("Error processing pubsub message")
        finally:
            await pubsub.unsubscribe(self._channel)
            await pubsub.aclose()
