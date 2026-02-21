"""Outbox worker: polls pending outbox records, publishes via Redis Pub/Sub."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis

from chat_service.config import settings
from chat_service.infrastructure.bus.redis_pubsub import RedisPubSubPublisher
from chat_service.infrastructure.db.session import AsyncSessionLocal
from chat_service.infrastructure.db.uow import SqlAlchemyUoW

logger = logging.getLogger(__name__)

BASE_DELAY_SECONDS = 5
MAX_DELAY_SECONDS = 300


def _calc_backoff(attempts: int) -> datetime:
    delay = min(BASE_DELAY_SECONDS * (2 ** attempts), MAX_DELAY_SECONDS)
    return datetime.now(timezone.utc) + timedelta(seconds=delay)


async def run_outbox_worker() -> None:
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    publisher = RedisPubSubPublisher(redis)

    logger.info(
        "Outbox worker started (poll=%.1fs, batch=%d, max_attempts=%d)",
        settings.OUTBOX_POLL_INTERVAL,
        settings.OUTBOX_BATCH_SIZE,
        settings.OUTBOX_MAX_ATTEMPTS,
    )

    try:
        while True:
            try:
                await _process_batch(publisher)
            except Exception:
                logger.exception("Outbox worker loop error")
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
    finally:
        await redis.aclose()


async def _process_batch(publisher: RedisPubSubPublisher) -> None:
    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        batch = await uow.outbox.fetch_pending(settings.OUTBOX_BATCH_SIZE)
        if not batch:
            return

        sent_ids: list[int] = []
        for record in batch:
            if record.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
                logger.warning("Outbox record %d exceeded max attempts, skipping", record.id)
                continue
            try:
                payload = {
                    "event_type": record.event_type,
                    **record.payload,
                }
                await publisher.publish(settings.REDIS_PUBSUB_CHANNEL, payload)
                sent_ids.append(record.id)
            except Exception:
                logger.exception("Failed to publish outbox record %d", record.id)
                await uow.outbox.mark_failed(record.id, _calc_backoff(record.attempts))

        if sent_ids:
            await uow.outbox.mark_sent(sent_ids)

        await uow.commit()
        if sent_ids:
            logger.info("Published %d outbox records", len(sent_ids))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run_outbox_worker())


if __name__ == "__main__":
    main()
