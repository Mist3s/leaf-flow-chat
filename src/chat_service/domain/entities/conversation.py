from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    topic_type: str
    topic_id: int | None
    status: str
    assignee_admin_id: int | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
