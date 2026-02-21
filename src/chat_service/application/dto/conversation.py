from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from chat_service.domain.value_objects.enums import ConversationStatus


@dataclass(frozen=True, slots=True)
class ConversationFilterDTO:
    status: ConversationStatus | None = None
    assignee_admin_id: int | None = None
    cursor: str | None = None
    limit: int = 20
