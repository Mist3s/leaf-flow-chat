from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConversationCreated:
    conversation_id: UUID
    user_id: int
    topic_type: str
