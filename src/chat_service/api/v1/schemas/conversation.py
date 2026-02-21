from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: UUID
    topic_type: str
    topic_id: int | None
    status: str
    assignee_admin_id: int | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
