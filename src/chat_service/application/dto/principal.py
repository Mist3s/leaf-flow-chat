from __future__ import annotations

from dataclasses import dataclass, field

from chat_service.domain.value_objects.enums import ParticipantKind


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller identity extracted from JWT."""

    kind: ParticipantKind
    subject_id: int
    roles: list[str] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return self.kind == ParticipantKind.ADMIN or "admin" in self.roles

    @property
    def principal_key(self) -> str:
        """Unique key for WS connection registry."""
        return f"{self.kind}:{self.subject_id}"
