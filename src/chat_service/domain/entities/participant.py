from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Participant:
    conversation_id: UUID
    kind: str
    subject_id: int
    joined_at: datetime
