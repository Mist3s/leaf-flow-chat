from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chat_service.application.dto.conversation import ConversationFilterDTO
from chat_service.domain.entities.conversation import Conversation
from chat_service.domain.value_objects.enums import ConversationStatus
from chat_service.infrastructure.db.mappers import conversation as mapper
from chat_service.infrastructure.db.models.conversation import ConversationModel
from chat_service.infrastructure.db.models.participant import ParticipantModel
from chat_service.infrastructure.db.repositories._cursor import decode_cursor, encode_cursor


class ConversationReaderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self._session.get(ConversationModel, conversation_id)
        return mapper.model_to_entity(result) if result else None

    async def get_support_for_user(self, user_id: int) -> Conversation | None:
        stmt = (
            select(ConversationModel)
            .join(
                ParticipantModel,
                ParticipantModel.conversation_id == ConversationModel.id,
            )
            .where(
                ParticipantModel.kind == "user",
                ParticipantModel.subject_id == user_id,
                ConversationModel.topic_type == "support",
                ConversationModel.status == ConversationStatus.OPEN,
            )
            .order_by(ConversationModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return mapper.model_to_entity(model) if model else None

    async def get_by_topic(
        self,
        topic_type: str,
        topic_id: int,
        *,
        status: str | None = None,
    ) -> Conversation | None:
        stmt = select(ConversationModel).where(
            ConversationModel.topic_type == topic_type,
            ConversationModel.topic_id == topic_id,
        )
        if status:
            stmt = stmt.where(ConversationModel.status == status)
        stmt = stmt.order_by(ConversationModel.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return mapper.model_to_entity(model) if model else None

    async def list_for_user(
        self,
        user_id: int,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> list[Conversation]:
        stmt = (
            select(ConversationModel)
            .join(
                ParticipantModel,
                ParticipantModel.conversation_id == ConversationModel.id,
            )
            .where(
                ParticipantModel.kind == "user",
                ParticipantModel.subject_id == user_id,
            )
            .order_by(ConversationModel.last_message_at.desc().nullslast(), ConversationModel.id)
            .limit(limit)
        )
        if cursor:
            ts, cid = decode_cursor(cursor)
            stmt = stmt.where(
                (ConversationModel.last_message_at < ts)
                | (
                    (ConversationModel.last_message_at == ts)
                    & (ConversationModel.id > cid)
                )
            )
        result = await self._session.execute(stmt)
        return [mapper.model_to_entity(m) for m in result.scalars().all()]

    async def list_for_admin(
        self,
        filters: ConversationFilterDTO,
    ) -> list[Conversation]:
        stmt = select(ConversationModel)
        if filters.status:
            stmt = stmt.where(ConversationModel.status == filters.status.value)
        if filters.assignee_admin_id is not None:
            stmt = stmt.where(ConversationModel.assignee_admin_id == filters.assignee_admin_id)
        stmt = stmt.order_by(
            ConversationModel.last_message_at.desc().nullslast(),
            ConversationModel.id,
        ).limit(filters.limit)
        if filters.cursor:
            ts, cid = decode_cursor(filters.cursor)
            stmt = stmt.where(
                (ConversationModel.last_message_at < ts)
                | (
                    (ConversationModel.last_message_at == ts)
                    & (ConversationModel.id > cid)
                )
            )
        result = await self._session.execute(stmt)
        return [mapper.model_to_entity(m) for m in result.scalars().all()]


class ConversationWriterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        model = mapper.entity_to_model(conversation)
        self._session.add(model)
        await self._session.flush()
        return mapper.model_to_entity(model)

    async def assign(self, conversation_id: UUID, admin_id: int | None) -> None:
        stmt = (
            update(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .values(assignee_admin_id=admin_id)
        )
        await self._session.execute(stmt)

    async def close(self, conversation_id: UUID) -> None:
        stmt = (
            update(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .values(status=ConversationStatus.CLOSED)
        )
        await self._session.execute(stmt)

    async def touch_last_message_at(
        self,
        conversation_id: UUID,
        ts: datetime,
    ) -> None:
        stmt = (
            update(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .values(last_message_at=ts)
        )
        await self._session.execute(stmt)
