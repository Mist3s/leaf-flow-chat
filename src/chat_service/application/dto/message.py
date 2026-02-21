from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from chat_service.domain.value_objects.enums import MessageType


@dataclass(frozen=True, slots=True)
class SendMessageDTO:
    conversation_id: UUID
    client_msg_id: UUID
    type: MessageType = MessageType.TEXT
    body: str | None = None
