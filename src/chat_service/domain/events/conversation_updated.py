from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConversationUpdated:
    conversation_id: UUID
    status: str | None = None
    assignee_admin_id: int | None = None
    action: str = ""  # "assigned" | "closed" | "reopened"
