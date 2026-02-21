from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from chat_service.application.dto.conversation import ConversationFilterDTO
from chat_service.domain.entities.conversation import Conversation


class ConversationReader(Protocol):
    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    async def get_support_for_user(self, user_id: int) -> Conversation | None:
        """Find an open support conversation where user is a participant."""
        ...

    async def get_by_topic(
        self, topic_type: str, topic_id: int, *, status: str | None = None,
    ) -> Conversation | None:
        """Find a conversation by topic_type + topic_id. Optionally filter by status."""
        ...

    async def list_for_user(
        self, user_id: int, *, cursor: str | None = None, limit: int = 20
    ) -> list[Conversation]: ...

    async def list_for_admin(
        self, filters: ConversationFilterDTO
    ) -> list[Conversation]: ...


class ConversationWriter(Protocol):
    async def create(self, conversation: Conversation) -> Conversation: ...

    async def assign(self, conversation_id: UUID, admin_id: int | None) -> None: ...

    async def close(self, conversation_id: UUID) -> None: ...

    async def touch_last_message_at(
        self, conversation_id: UUID, ts: datetime
    ) -> None: ...
