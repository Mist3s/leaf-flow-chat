from __future__ import annotations

import uuid
from datetime import datetime, timezone

from chat_service.application.dto.principal import Principal
from chat_service.application.exceptions import NotFoundError
from chat_service.application.policies.permissions import assert_conversation_access
from chat_service.application.uow import UnitOfWork
from chat_service.domain.entities.conversation import Conversation
from chat_service.domain.entities.participant import Participant
from chat_service.domain.value_objects.enums import ConversationStatus, ParticipantKind


async def get_or_create_support_conversation(
    user_id: int,
    uow: UnitOfWork,
) -> Conversation:
    """Return an existing open support conversation for the user, or create a new one."""
    existing = await uow.conversations.get_support_for_user(user_id)
    if existing is not None:
        return existing

    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=uuid.uuid4(),
        topic_type="support",
        topic_id=None,
        status=ConversationStatus.OPEN,
        assignee_admin_id=None,
        last_message_at=None,
        created_at=now,
        updated_at=now,
    )
    conversation = await uow.conversations_w.create(conversation)

    participant = Participant(
        conversation_id=conversation.id,
        kind=ParticipantKind.USER,
        subject_id=user_id,
        joined_at=now,
    )
    await uow.participants_w.add(participant)

    await uow.outbox.add(
        "chat.conversation_created",
        {
            "conversation_id": str(conversation.id),
            "user_id": user_id,
            "topic_type": "support",
        },
    )
    await uow.commit()
    return conversation


async def get_or_create_topic_conversation(
    topic_type: str,
    topic_id: int,
    user_id: int,
    uow: UnitOfWork,
) -> tuple[Conversation, bool]:
    """Return existing open conversation for topic or create a new one.

    Returns (conversation, created) where created=True if a new conversation was made.
    """
    existing = await uow.conversations.get_by_topic(
        topic_type, topic_id, status=ConversationStatus.OPEN,
    )
    if existing is not None:
        return existing, False

    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=uuid.uuid4(),
        topic_type=topic_type,
        topic_id=topic_id,
        status=ConversationStatus.OPEN,
        assignee_admin_id=None,
        last_message_at=None,
        created_at=now,
        updated_at=now,
    )
    conversation = await uow.conversations_w.create(conversation)

    participant = Participant(
        conversation_id=conversation.id,
        kind=ParticipantKind.USER,
        subject_id=user_id,
        joined_at=now,
    )
    await uow.participants_w.add(participant)

    await uow.outbox.add(
        "chat.conversation_created",
        {
            "conversation_id": str(conversation.id),
            "user_id": user_id,
            "topic_type": topic_type,
            "topic_id": topic_id,
        },
    )
    await uow.commit()
    return conversation, True


async def list_user_conversations(
    principal: Principal,
    cursor: str | None,
    limit: int,
    uow: UnitOfWork,
) -> list[Conversation]:
    return await uow.conversations.list_for_user(
        principal.subject_id, cursor=cursor, limit=limit,
    )


async def get_conversation(
    conversation_id: uuid.UUID,
    principal: Principal,
    uow: UnitOfWork,
) -> Conversation:
    conversation = await uow.conversations.get_by_id(conversation_id)
    return await assert_conversation_access(principal, conversation, uow.participants)
