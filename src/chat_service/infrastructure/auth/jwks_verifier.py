from __future__ import annotations

import logging

import jwt
from jwt import PyJWKClient

from chat_service.application.dto.principal import Principal
from chat_service.domain.value_objects.enums import ParticipantKind

logger = logging.getLogger(__name__)


class JWKSVerifier:
    """Verify JWTs using a remote JWKS endpoint."""

    def __init__(self, jwks_url: str) -> None:
        self._jwks_url = jwks_url
        self._jwk_client = PyJWKClient(jwks_url)

    async def verify(self, token: str) -> Principal:
        signing_key = self._jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
        )
        kind_raw = payload.get("kind", payload.get("role", "user"))
        kind = ParticipantKind(kind_raw) if kind_raw in ParticipantKind.__members__.values() else ParticipantKind.USER
        return Principal(
            kind=kind,
            subject_id=int(payload["sub"]),
            roles=payload.get("roles", []),
        )
