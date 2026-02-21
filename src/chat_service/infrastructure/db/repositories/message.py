from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from chat_service.domain.entities.message import Message
from chat_service.infrastructure.db.mappers import message as mapper
from chat_service.infrastructure.db.models.message import MessageModel
from chat_service.infrastructure.db.repositories._cursor import decode_cursor


class MessageReaderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_messages(
        self,
        conversation_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 50,
    ) -> list[Message]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc(), MessageModel.id.asc())
            .limit(limit)
        )
        if cursor:
            ts, mid = decode_cursor(cursor)
            stmt = stmt.where(
                (MessageModel.created_at > ts)
                | ((MessageModel.created_at == ts) & (MessageModel.id > mid))
            )
        result = await self._session.execute(stmt)
        return [mapper.model_to_entity(m) for m in result.scalars().all()]


class MessageWriterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_if_not_exists(self, message: Message) -> tuple[Message, bool]:
        """Insert message idempotently. Returns (message, created_flag)."""
        model = mapper.entity_to_model(message)
        values = {
            "id": model.id,
            "conversation_id": model.conversation_id,
            "sender_kind": model.sender_kind,
            "sender_id": model.sender_id,
            "type": model.type,
            "body": model.body,
            "payload": model.payload,
            "client_msg_id": model.client_msg_id,
            "created_at": model.created_at,
        }
        stmt = (
            pg_insert(MessageModel)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_message_idempotency")
            .returning(MessageModel)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is not None:
            # Inserted successfully
            return mapper.model_to_entity(row), True

        # Conflict — fetch existing
        existing = await self.get_by_client_msg_id(
            message.conversation_id,
            message.sender_kind,
            message.sender_id,
            message.client_msg_id,
        )
        assert existing is not None
        return existing, False

    async def get_by_client_msg_id(
        self,
        conversation_id: UUID,
        sender_kind: str,
        sender_id: int,
        client_msg_id: UUID,
    ) -> Message | None:
        stmt = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id,
            MessageModel.sender_kind == sender_kind,
            MessageModel.sender_id == sender_id,
            MessageModel.client_msg_id == client_msg_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return mapper.model_to_entity(model) if model else None
