from __future__ import annotations

from typing import Protocol

from chat_service.application.repositories.conversation import (
    ConversationReader,
    ConversationWriter,
)
from chat_service.application.repositories.message import MessageReader, MessageWriter
from chat_service.application.repositories.outbox import OutboxWriter
from chat_service.application.repositories.participant import (
    ParticipantReader,
    ParticipantWriter,
)
from chat_service.application.repositories.read_state import ReadStateWriter


class UnitOfWork(Protocol):
    conversations: ConversationReader
    conversations_w: ConversationWriter
    participants: ParticipantReader
    participants_w: ParticipantWriter
    messages: MessageReader
    messages_w: MessageWriter
    read_state_w: ReadStateWriter
    outbox: OutboxWriter

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def flush(self) -> None: ...
