from __future__ import annotations

import uuid
from datetime import datetime, timezone

from chat_service.application.dto.conversation import ConversationFilterDTO
from chat_service.application.dto.principal import Principal
from chat_service.application.exceptions import NotFoundError
from chat_service.application.policies.permissions import assert_admin
from chat_service.application.uow import UnitOfWork
from chat_service.domain.entities.conversation import Conversation
from chat_service.domain.entities.message import Message
from chat_service.domain.value_objects.enums import ConversationStatus, MessageType, ParticipantKind


async def list_conversations(
    filters: ConversationFilterDTO,
    uow: UnitOfWork,
) -> list[Conversation]:
    return await uow.conversations.list_for_admin(filters)


async def get_conversation(
    conversation_id: uuid.UUID,
    uow: UnitOfWork,
) -> Conversation:
    conversation = await uow.conversations.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return conversation


async def assign_conversation(
    conversation_id: uuid.UUID,
    admin_id: int,
    principal: Principal,
    uow: UnitOfWork,
) -> Conversation:
    assert_admin(principal)
    conversation = await uow.conversations.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")

    await uow.conversations_w.assign(conversation_id, admin_id)

    is_participant = await uow.participants.is_participant(
        conversation_id, ParticipantKind.ADMIN, admin_id,
    )
    if not is_participant:
        from chat_service.domain.entities.participant import Participant

        await uow.participants_w.add(
            Participant(
                conversation_id=conversation_id,
                kind=ParticipantKind.ADMIN,
                subject_id=admin_id,
                joined_at=datetime.now(timezone.utc),
            )
        )

    now = datetime.now(timezone.utc)
    system_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        sender_kind=ParticipantKind.ADMIN,
        sender_id=admin_id,
        type=MessageType.SYSTEM,
        body=f"Admin {admin_id} assigned to conversation",
        payload={"action": "assigned", "admin_id": admin_id},
        client_msg_id=uuid.uuid4(),
        created_at=now,
    )
    await uow.messages_w.create_if_not_exists(system_msg)
    await uow.conversations_w.touch_last_message_at(conversation_id, now)

    await uow.outbox.add(
        "chat.conversation_updated",
        {
            "conversation_id": str(conversation_id),
            "action": "assigned",
            "assignee_admin_id": admin_id,
        },
    )
    await uow.commit()
    return await uow.conversations.get_by_id(conversation_id)  # type: ignore[return-value]


async def close_conversation(
    conversation_id: uuid.UUID,
    principal: Principal,
    uow: UnitOfWork,
) -> Conversation:
    assert_admin(principal)
    conversation = await uow.conversations.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")

    await uow.conversations_w.close(conversation_id)

    now = datetime.now(timezone.utc)
    system_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        sender_kind=ParticipantKind.ADMIN,
        sender_id=principal.subject_id,
        type=MessageType.SYSTEM,
        body="Conversation closed",
        payload={"action": "closed"},
        client_msg_id=uuid.uuid4(),
        created_at=now,
    )
    await uow.messages_w.create_if_not_exists(system_msg)
    await uow.conversations_w.touch_last_message_at(conversation_id, now)

    await uow.outbox.add(
        "chat.conversation_updated",
        {
            "conversation_id": str(conversation_id),
            "action": "closed",
            "status": ConversationStatus.CLOSED,
        },
    )
    await uow.commit()
    return await uow.conversations.get_by_id(conversation_id)  # type: ignore[return-value]
