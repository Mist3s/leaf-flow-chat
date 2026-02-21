"""Shared test fixtures."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest

from chat_service.application.dto.principal import Principal
from chat_service.application.repositories.outbox import OutboxRecord
from chat_service.domain.entities.conversation import Conversation
from chat_service.domain.entities.message import Message
from chat_service.domain.entities.participant import Participant
from chat_service.domain.value_objects.enums import (
    ConversationStatus,
    MessageType,
    ParticipantKind,
)


@pytest.fixture
def user_principal() -> Principal:
    return Principal(kind=ParticipantKind.USER, subject_id=42, roles=[])


@pytest.fixture
def admin_principal() -> Principal:
    return Principal(kind=ParticipantKind.ADMIN, subject_id=1, roles=["admin"])


def make_conversation(
    *,
    conversation_id: UUID | None = None,
    status: str = ConversationStatus.OPEN,
    assignee: int | None = None,
) -> Conversation:
    now = datetime.now(timezone.utc)
    return Conversation(
        id=conversation_id or uuid.uuid4(),
        topic_type="support",
        topic_id=None,
        status=status,
        assignee_admin_id=assignee,
        last_message_at=None,
        created_at=now,
        updated_at=now,
    )


def make_message(
    *,
    conversation_id: UUID | None = None,
    sender_kind: str = ParticipantKind.USER,
    sender_id: int = 42,
    body: str = "hello",
) -> Message:
    return Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id or uuid.uuid4(),
        sender_kind=sender_kind,
        sender_id=sender_id,
        type=MessageType.TEXT,
        body=body,
        payload=None,
        client_msg_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


@dataclass
class FakeConversationReader:
    _store: dict[UUID, Conversation] = field(default_factory=dict)
    _user_convs: dict[int, list[Conversation]] = field(default_factory=dict)

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self._store.get(conversation_id)

    async def get_support_for_user(self, user_id: int) -> Conversation | None:
        for c in self._user_convs.get(user_id, []):
            if c.status == ConversationStatus.OPEN and c.topic_type == "support":
                return c
        return None

    async def list_for_user(self, user_id: int, *, cursor: str | None = None, limit: int = 20) -> list[Conversation]:
        return self._user_convs.get(user_id, [])[:limit]

    async def list_for_admin(self, filters: Any) -> list[Conversation]:
        return list(self._store.values())


@dataclass
class FakeConversationWriter:
    _reader: FakeConversationReader

    async def create(self, conversation: Conversation) -> Conversation:
        self._reader._store[conversation.id] = conversation
        return conversation

    async def assign(self, conversation_id: UUID, admin_id: int | None) -> None:
        pass

    async def close(self, conversation_id: UUID) -> None:
        pass

    async def touch_last_message_at(self, conversation_id: UUID, ts: datetime) -> None:
        pass


@dataclass
class FakeParticipantReader:
    _participants: list[Participant] = field(default_factory=list)

    async def is_participant(self, conversation_id: UUID, kind: str, subject_id: int) -> bool:
        return any(
            p.conversation_id == conversation_id and p.kind == kind and p.subject_id == subject_id
            for p in self._participants
        )

    async def list_participants(self, conversation_id: UUID) -> list[Participant]:
        return [p for p in self._participants if p.conversation_id == conversation_id]


@dataclass
class FakeParticipantWriter:
    _reader: FakeParticipantReader

    async def add(self, participant: Participant) -> None:
        self._reader._participants.append(participant)


@dataclass
class FakeMessageReader:
    _messages: list[Message] = field(default_factory=list)

    async def list_messages(self, conversation_id: UUID, *, cursor: str | None = None, limit: int = 50) -> list[Message]:
        return [m for m in self._messages if m.conversation_id == conversation_id][:limit]


@dataclass
class FakeMessageWriter:
    _reader: FakeMessageReader
    _created_ids: set[UUID] = field(default_factory=set)

    async def create_if_not_exists(self, message: Message) -> tuple[Message, bool]:
        for m in self._reader._messages:
            if (
                m.conversation_id == message.conversation_id
                and m.sender_kind == message.sender_kind
                and m.sender_id == message.sender_id
                and m.client_msg_id == message.client_msg_id
            ):
                return m, False
        self._reader._messages.append(message)
        self._created_ids.add(message.id)
        return message, True

    async def get_by_client_msg_id(self, conversation_id: UUID, sender_kind: str, sender_id: int, client_msg_id: UUID) -> Message | None:
        for m in self._reader._messages:
            if m.conversation_id == conversation_id and m.client_msg_id == client_msg_id:
                return m
        return None


@dataclass
class FakeReadStateWriter:
    _states: list[tuple] = field(default_factory=list)

    async def upsert_last_read(self, conversation_id: UUID, kind: str, subject_id: int, last_message_id: UUID) -> None:
        self._states.append((conversation_id, kind, subject_id, last_message_id))


@dataclass
class FakeOutboxWriter:
    _records: list[dict[str, Any]] = field(default_factory=list)

    async def add(self, event_type: str, payload: dict[str, Any]) -> None:
        self._records.append({"event_type": event_type, "payload": payload})

    async def fetch_pending(self, batch_size: int) -> list[OutboxRecord]:
        return []

    async def mark_sent(self, ids: list[int]) -> None:
        pass

    async def mark_failed(self, record_id: int, next_retry_at: datetime) -> None:
        pass


@dataclass
class FakeUoW:
    """In-memory UoW for unit tests."""
    conversations: FakeConversationReader = field(default_factory=FakeConversationReader)
    conversations_w: FakeConversationWriter | None = None
    participants: FakeParticipantReader = field(default_factory=FakeParticipantReader)
    participants_w: FakeParticipantWriter | None = None
    messages: FakeMessageReader = field(default_factory=FakeMessageReader)
    messages_w: FakeMessageWriter | None = None
    read_state_w: FakeReadStateWriter = field(default_factory=FakeReadStateWriter)
    outbox: FakeOutboxWriter = field(default_factory=FakeOutboxWriter)
    _committed: bool = False

    def __post_init__(self) -> None:
        if self.conversations_w is None:
            self.conversations_w = FakeConversationWriter(self.conversations)
        if self.participants_w is None:
            self.participants_w = FakeParticipantWriter(self.participants)
        if self.messages_w is None:
            self.messages_w = FakeMessageWriter(self.messages)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        pass
