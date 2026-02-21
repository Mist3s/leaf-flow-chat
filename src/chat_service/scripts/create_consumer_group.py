"""One-time script: create Redis Streams consumer group for LeafFlow events."""
from __future__ import annotations

import asyncio
import logging

import redis.asyncio as aioredis

from chat_service.config import settings

logger = logging.getLogger(__name__)


async def create_group() -> None:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.xgroup_create(
            settings.LEAF_EVENTS_STREAM,
            settings.LEAF_EVENTS_GROUP,
            id="$",
            mkstream=True,
        )
        logger.info(
            "Created consumer group '%s' on stream '%s'",
            settings.LEAF_EVENTS_GROUP,
            settings.LEAF_EVENTS_STREAM,
        )
    except aioredis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group '%s' already exists", settings.LEAF_EVENTS_GROUP)
        else:
            raise
    finally:
        await r.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_group())


if __name__ == "__main__":
    main()
