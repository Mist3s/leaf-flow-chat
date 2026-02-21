from __future__ import annotations

import uuid

from chat_service.application.dto.principal import Principal
from chat_service.application.policies.permissions import assert_conversation_access
from chat_service.application.uow import UnitOfWork


async def mark_read(
    conversation_id: uuid.UUID,
    principal: Principal,
    last_message_id: uuid.UUID,
    uow: UnitOfWork,
) -> None:
    conversation = await uow.conversations.get_by_id(conversation_id)
    await assert_conversation_access(principal, conversation, uow.participants)
    await uow.read_state_w.upsert_last_read(
        conversation_id,
        principal.kind.value,
        principal.subject_id,
        last_message_id,
    )
    await uow.commit()
