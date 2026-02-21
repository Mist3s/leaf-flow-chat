from __future__ import annotations

from enum import StrEnum


class ConversationStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class ParticipantKind(StrEnum):
    USER = "user"
    ADMIN = "admin"


class MessageType(StrEnum):
    TEXT = "text"
    SYSTEM = "system"
    ATTACHMENT = "attachment"
