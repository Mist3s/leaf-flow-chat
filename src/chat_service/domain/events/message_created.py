from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MessageCreated:
    message_id: UUID
    conversation_id: UUID
    sender_kind: str
    sender_id: int
    body: str | None
