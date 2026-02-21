from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ReadStateWriter(Protocol):
    async def upsert_last_read(
        self,
        conversation_id: UUID,
        kind: str,
        subject_id: int,
        last_message_id: UUID,
    ) -> None: ...
