from __future__ import annotations

import jwt

from chat_service.application.dto.principal import Principal
from chat_service.domain.value_objects.enums import ParticipantKind


class HS256Verifier:
    """Verify JWTs signed with a shared HS256 secret."""

    def __init__(self, secret: str, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._algorithm = algorithm

    async def verify(self, token: str) -> Principal:
        payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        kind_raw = payload.get("kind", payload.get("role", "user"))
        kind = ParticipantKind(kind_raw) if kind_raw in ParticipantKind.__members__.values() else ParticipantKind.USER
        return Principal(
            kind=kind,
            subject_id=int(payload["sub"]),
            roles=payload.get("roles", []),
        )
