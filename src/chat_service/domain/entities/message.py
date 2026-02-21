from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Message:
    id: UUID
    conversation_id: UUID
    sender_kind: str
    sender_id: int
    type: str
    body: str | None
    payload: dict[str, Any] | None
    client_msg_id: UUID
    created_at: datetime
