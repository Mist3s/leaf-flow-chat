from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReadState:
    conversation_id: UUID
    kind: str
    subject_id: int
    last_read_message_id: UUID | None
    updated_at: datetime
