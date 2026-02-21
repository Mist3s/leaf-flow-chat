from __future__ import annotations

from typing import Protocol
from uuid import UUID

from chat_service.domain.entities.participant import Participant


class ParticipantReader(Protocol):
    async def is_participant(
        self,
        conversation_id: UUID,
        kind: str,
        subject_id: int,
    ) -> bool: ...

    async def list_participants(
        self, conversation_id: UUID
    ) -> list[Participant]: ...


class ParticipantWriter(Protocol):
    async def add(self, participant: Participant) -> None: ...
