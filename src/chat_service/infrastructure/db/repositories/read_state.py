from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from chat_service.infrastructure.db.models.read_state import ReadStateModel


class ReadStateWriterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_last_read(
        self,
        conversation_id: UUID,
        kind: str,
        subject_id: int,
        last_message_id: UUID,
    ) -> None:
        stmt = (
            pg_insert(ReadStateModel)
            .values(
                conversation_id=conversation_id,
                kind=kind,
                subject_id=subject_id,
                last_read_message_id=last_message_id,
            )
            .on_conflict_do_update(
                constraint="uq_read_state_member",
                set_={"last_read_message_id": last_message_id},
            )
        )
        await self._session.execute(stmt)
