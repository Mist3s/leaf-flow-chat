from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from chat_service.domain.value_objects.enums import MessageType


class SendMessageRequest(BaseModel):
    client_msg_id: UUID
    type: MessageType = MessageType.TEXT
    body: str | None = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_kind: str
    sender_id: int
    type: str
    body: str | None
    payload: dict[str, Any] | None
    client_msg_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
