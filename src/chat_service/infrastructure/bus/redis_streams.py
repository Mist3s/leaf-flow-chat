"""Redis Streams consumer for external LeafFlow events."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

OnStreamEventCallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class RedisStreamConsumer:
    """XREADGROUP-based consumer for a single stream + consumer group."""

    def __init__(
        self,
        redis: aioredis.Redis,
        stream: str,
        group: str,
        consumer: str,
        callback: OnStreamEventCallback,
        *,
        batch_size: int = 10,
        block_ms: int = 5000,
    ) -> None:
        self._redis = redis
        self._stream = stream
        self._group = group
        self._consumer = consumer
        self._callback = callback
        self._batch_size = batch_size
        self._block_ms = block_ms
        self._task: asyncio.Task[None] | None = None

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._stream, self._group, id="$", mkstream=True
            )
            logger.info("Created consumer group %s on %s", self._group, self._stream)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group %s already exists", self._group)
            else:
                raise

    async def start(self) -> None:
        await self.ensure_group()
        self._task = asyncio.create_task(self._consume(), name="redis-stream-consumer")
        logger.info("Stream consumer started: stream=%s group=%s", self._stream, self._group)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Stream consumer stopped")

    async def _consume(self) -> None:
        while True:
            try:
                entries = await self._redis.xreadgroup(
                    groupname=self._group,
                    consumername=self._consumer,
                    streams={self._stream: ">"},
                    count=self._batch_size,
                    block=self._block_ms,
                )
                if not entries:
                    continue
                for _stream_name, messages in entries:
                    for msg_id, fields in messages:
                        event_type = fields.get("event_type", "unknown")
                        try:
                            await self._callback(event_type, fields)
                            await self._redis.xack(self._stream, self._group, msg_id)
                        except Exception:
                            logger.exception(
                                "Error processing stream message %s", msg_id
                            )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Stream consumer error, retrying in 5s")
                await asyncio.sleep(5)
