from __future__ import annotations

from pydantic import BaseModel

from chat_service.domain.value_objects.enums import ConversationStatus


class AdminConversationFilters(BaseModel):
    status: ConversationStatus | None = None
    assignee_admin_id: int | None = None
    cursor: str | None = None
    limit: int = 20


class PatchConversationRequest(BaseModel):
    assignee_admin_id: int | None = None
    status: ConversationStatus | None = None
