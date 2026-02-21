"""Consumer for external LeafFlow events via Redis Streams."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis

from chat_service.application.dto.principal import Principal
from chat_service.config import settings
from chat_service.domain.value_objects.enums import MessageType, ParticipantKind
from chat_service.infrastructure.bus.redis_streams import RedisStreamConsumer
from chat_service.infrastructure.db.session import AsyncSessionLocal
from chat_service.infrastructure.db.uow import SqlAlchemyUoW
from chat_service.services import conversation_service, message_service

logger = logging.getLogger(__name__)


async def _handle_event(event_type: str, fields: dict[str, Any]) -> None:
    """Dispatch a stream event to the appropriate handler."""
    if event_type == "user.blocked":
        await _handle_user_blocked(fields)
    elif event_type == "user.updated":
        await _handle_user_updated(fields)
    elif event_type == "order.created":
        await _handle_order_created(fields)
    elif event_type == "order.status_changed":
        await _handle_order_status_changed(fields)
    else:
        logger.debug("Ignoring unknown event: %s", event_type)


async def _handle_user_blocked(fields: dict[str, Any]) -> None:
    user_id = fields.get("user_id")
    logger.info("User %s blocked — future send_message calls will be rejected", user_id)
    # TODO: persist blocked state, check in send_message


async def _handle_user_updated(fields: dict[str, Any]) -> None:
    user_id = fields.get("user_id")
    logger.debug("User %s updated (no-op for now)", user_id)


async def _handle_order_created(fields: dict[str, Any]) -> None:
    """Create a chat conversation tied to a new order."""
    user_id = int(fields["user_id"])
    order_id = int(fields["order_id"])

    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        conv, created = await conversation_service.get_or_create_topic_conversation(
            "order", order_id, user_id, uow,
        )

    if created:
        logger.info(
            "Created conversation %s for order %d (user %d)",
            conv.id, order_id, user_id,
        )
    else:
        logger.debug(
            "Conversation %s already exists for order %d",
            conv.id, order_id,
        )


_SYSTEM_PRINCIPAL = Principal(kind=ParticipantKind.ADMIN, subject_id=0, roles=["admin"])

_ORDER_STATUS_LABELS: dict[str, str] = {
    "confirmed": "Заказ подтверждён",
    "processing": "Заказ в обработке",
    "shipped": "Заказ отправлен",
    "delivered": "Заказ доставлен",
    "completed": "Заказ завершён",
    "cancelled": "Заказ отменён",
    "refunded": "Возврат оформлен",
}


async def _handle_order_status_changed(fields: dict[str, Any]) -> None:
    """Send a system message to the order conversation when status changes."""
    order_id = int(fields["order_id"])
    new_status = fields["status"]
    old_status = fields.get("old_status")

    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        conv = await uow.conversations.get_by_topic("order", order_id)
        if conv is None:
            logger.warning(
                "No conversation for order %d, cannot notify about status %s",
                order_id, new_status,
            )
            return

        label = _ORDER_STATUS_LABELS.get(new_status, f"Статус заказа: {new_status}")
        body = f"{label} (#{order_id})"

        await message_service.send_message(
            conv.id, _SYSTEM_PRINCIPAL, uuid.uuid4(),
            MessageType.SYSTEM, body, uow,
        )

    logger.info(
        "Order %d status %s → %s — notified in conversation %s",
        order_id, old_status or "?", new_status, conv.id,
    )


async def run_consumer() -> None:
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    consumer_name = f"consumer-{uuid.uuid4().hex[:8]}"

    consumer = RedisStreamConsumer(
        redis=redis,
        stream=settings.LEAF_EVENTS_STREAM,
        group=settings.LEAF_EVENTS_GROUP,
        consumer=consumer_name,
        callback=_handle_event,
    )
    await consumer.start()
    logger.info("LeafFlow events consumer started (%s)", consumer_name)

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
        await redis.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run_consumer())


if __name__ == "__main__":
    main()
