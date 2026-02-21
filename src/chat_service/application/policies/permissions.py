from __future__ import annotations

from uuid import UUID

from chat_service.application.dto.principal import Principal
from chat_service.application.exceptions import ForbiddenError, NotFoundError
from chat_service.application.repositories.participant import ParticipantReader
from chat_service.domain.entities.conversation import Conversation


async def assert_conversation_access(
    principal: Principal,
    conversation: Conversation | None,
    participants: ParticipantReader,
) -> Conversation:
    """Raise if conversation doesn't exist or principal has no access."""
    if conversation is None:
        raise NotFoundError("Conversation not found")

    # Admins have global access
    if principal.is_admin:
        return conversation

    is_member = await participants.is_participant(
        conversation.id, principal.kind.value, principal.subject_id
    )
    if not is_member:
        raise ForbiddenError("Not a participant of this conversation")

    return conversation


def assert_admin(principal: Principal) -> None:
    if not principal.is_admin:
        raise ForbiddenError("Admin access required")
