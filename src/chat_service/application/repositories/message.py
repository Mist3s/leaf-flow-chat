from __future__ import annotations

from typing import Protocol
from uuid import UUID

from chat_service.domain.entities.message import Message


class MessageReader(Protocol):
    async def list_messages(
        self,
        conversation_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 50,
    ) -> list[Message]: ...


class MessageWriter(Protocol):
    async def create_if_not_exists(self, message: Message) -> tuple[Message, bool]:
        """Insert message. Return (message, created). If conflict on client_msg_id → return existing."""
        ...

    async def get_by_client_msg_id(
        self,
        conversation_id: UUID,
        sender_kind: str,
        sender_id: int,
        client_msg_id: UUID,
    ) -> Message | None: ...
