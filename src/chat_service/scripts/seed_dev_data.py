"""Seed development data: creates sample conversations and messages."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from chat_service.infrastructure.db.session import AsyncSessionLocal
from chat_service.infrastructure.db.uow import SqlAlchemyUoW
from chat_service.domain.entities.conversation import Conversation
from chat_service.domain.entities.message import Message
from chat_service.domain.entities.participant import Participant
from chat_service.domain.value_objects.enums import (
    ConversationStatus,
    MessageType,
    ParticipantKind,
)

logger = logging.getLogger(__name__)


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        now = datetime.now(timezone.utc)

        conv_id = uuid.uuid4()
        conv = Conversation(
            id=conv_id,
            topic_type="support",
            topic_id=None,
            status=ConversationStatus.OPEN,
            assignee_admin_id=None,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        await uow.conversations_w.create(conv)

        await uow.participants_w.add(
            Participant(conversation_id=conv_id, kind=ParticipantKind.USER, subject_id=42, joined_at=now)
        )
        await uow.participants_w.add(
            Participant(conversation_id=conv_id, kind=ParticipantKind.ADMIN, subject_id=1, joined_at=now)
        )

        messages_data = [
            ("user", 42, "Привет! У меня проблема с заказом."),
            ("admin", 1, "Здравствуйте! Какой номер заказа?"),
            ("user", 42, "Заказ #12345"),
            ("admin", 1, "Спасибо, проверяю. Одну минуту."),
        ]
        for sender_kind, sender_id, body in messages_data:
            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conv_id,
                sender_kind=sender_kind,
                sender_id=sender_id,
                type=MessageType.TEXT,
                body=body,
                payload=None,
                client_msg_id=uuid.uuid4(),
                created_at=now,
            )
            await uow.messages_w.create_if_not_exists(msg)

        await uow.commit()
        logger.info("Seeded conversation %s with %d messages", conv_id, len(messages_data))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())


if __name__ == "__main__":
    main()
