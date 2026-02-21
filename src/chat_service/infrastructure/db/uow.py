from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from chat_service.infrastructure.db.repositories.conversation import (
    ConversationReaderRepo,
    ConversationWriterRepo,
)
from chat_service.infrastructure.db.repositories.message import (
    MessageReaderRepo,
    MessageWriterRepo,
)
from chat_service.infrastructure.db.repositories.outbox import OutboxWriterRepo
from chat_service.infrastructure.db.repositories.participant import (
    ParticipantReaderRepo,
    ParticipantWriterRepo,
)
from chat_service.infrastructure.db.repositories.read_state import ReadStateWriterRepo


class SqlAlchemyUoW:
    """Concrete Unit-of-Work backed by a single AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.conversations = ConversationReaderRepo(session)
        self.conversations_w = ConversationWriterRepo(session)
        self.participants = ParticipantReaderRepo(session)
        self.participants_w = ParticipantWriterRepo(session)
        self.messages = MessageReaderRepo(session)
        self.messages_w = MessageWriterRepo(session)
        self.read_state_w = ReadStateWriterRepo(session)
        self.outbox = OutboxWriterRepo(session)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
