from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chat_service.application.repositories.outbox import OutboxRecord
from chat_service.infrastructure.db.models.outbox import OutboxMessageModel


class OutboxWriterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event_type: str, payload: dict[str, Any]) -> None:
        model = OutboxMessageModel(event_type=event_type, payload=payload)
        self._session.add(model)
        await self._session.flush()

    async def fetch_pending(self, batch_size: int) -> list[OutboxRecord]:
        stmt = (
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.status.in_(["pending", "failed"]),
                (
                    OutboxMessageModel.next_retry_at.is_(None)
                    | (OutboxMessageModel.next_retry_at <= datetime.utcnow())
                ),
            )
            .order_by(OutboxMessageModel.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        # Mark as processing
        if rows:
            ids = [r.id for r in rows]
            await self._session.execute(
                update(OutboxMessageModel)
                .where(OutboxMessageModel.id.in_(ids))
                .values(status="processing")
            )
            await self._session.flush()

        return [
            OutboxRecord(
                id=r.id,
                event_type=r.event_type,
                payload=r.payload,
                attempts=r.attempts,
            )
            for r in rows
        ]

    async def mark_sent(self, ids: list[int]) -> None:
        if not ids:
            return
        stmt = (
            update(OutboxMessageModel)
            .where(OutboxMessageModel.id.in_(ids))
            .values(status="sent")
        )
        await self._session.execute(stmt)

    async def mark_failed(self, record_id: int, next_retry_at: datetime) -> None:
        stmt = (
            update(OutboxMessageModel)
            .where(OutboxMessageModel.id == record_id)
            .values(
                status="failed",
                attempts=OutboxMessageModel.attempts + 1,
                next_retry_at=next_retry_at,
            )
        )
        await self._session.execute(stmt)
