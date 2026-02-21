from __future__ import annotations

import uuid
from datetime import datetime, timezone

from chat_service.application.dto.principal import Principal
from chat_service.application.policies.permissions import assert_conversation_access
from chat_service.application.uow import UnitOfWork
from chat_service.domain.entities.message import Message
from chat_service.domain.value_objects.enums import MessageType


async def send_message(
    conversation_id: uuid.UUID,
    principal: Principal,
    client_msg_id: uuid.UUID,
    msg_type: MessageType,
    body: str | None,
    uow: UnitOfWork,
) -> tuple[Message, bool]:
    """Create a message idempotently.

    Returns (message, created). If a message with the same client_msg_id
    already exists the existing one is returned with created=False.
    """
    conversation = await uow.conversations.get_by_id(conversation_id)
    await assert_conversation_access(principal, conversation, uow.participants)

    now = datetime.now(timezone.utc)
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        sender_kind=principal.kind.value,
        sender_id=principal.subject_id,
        type=msg_type.value,
        body=body,
        payload=None,
        client_msg_id=client_msg_id,
        created_at=now,
    )

    msg, created = await uow.messages_w.create_if_not_exists(msg)

    if created:
        await uow.conversations_w.touch_last_message_at(conversation_id, msg.created_at)
        await uow.outbox.add(
            "chat.message_created",
            {
                "message_id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "sender_kind": msg.sender_kind,
                "sender_id": msg.sender_id,
                "type": msg.type,
                "body": msg.body,
            },
        )
        await uow.commit()

    return msg, created


async def list_messages(
    conversation_id: uuid.UUID,
    principal: Principal,
    cursor: str | None,
    limit: int,
    uow: UnitOfWork,
) -> list[Message]:
    conversation = await uow.conversations.get_by_id(conversation_id)
    await assert_conversation_access(principal, conversation, uow.participants)
    return await uow.messages.list_messages(
        conversation_id, cursor=cursor, limit=limit,
    )
