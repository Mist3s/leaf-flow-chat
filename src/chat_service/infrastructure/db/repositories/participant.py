from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chat_service.domain.entities.participant import Participant
from chat_service.infrastructure.db.mappers import participant as mapper
from chat_service.infrastructure.db.models.participant import ParticipantModel


class ParticipantReaderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_participant(
        self,
        conversation_id: UUID,
        kind: str,
        subject_id: int,
    ) -> bool:
        stmt = (
            select(ParticipantModel.id)
            .where(
                ParticipantModel.conversation_id == conversation_id,
                ParticipantModel.kind == kind,
                ParticipantModel.subject_id == subject_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_participants(self, conversation_id: UUID) -> list[Participant]:
        stmt = select(ParticipantModel).where(
            ParticipantModel.conversation_id == conversation_id
        )
        result = await self._session.execute(stmt)
        return [mapper.model_to_entity(m) for m in result.scalars().all()]


class ParticipantWriterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, participant: Participant) -> None:
        model = mapper.entity_to_model(participant)
        self._session.add(model)
        await self._session.flush()
