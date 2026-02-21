from __future__ import annotations

import uuid

import pytest

from chat_service.domain.entities.participant import Participant
from chat_service.domain.value_objects.enums import MessageType, ParticipantKind
from chat_service.services import message_service
from tests.conftest import FakeUoW, make_conversation


@pytest.fixture
def uow_with_conversation(user_principal, admin_principal):
    uow = FakeUoW()
    conv = make_conversation()
    uow.conversations._store[conv.id] = conv
    uow.participants._participants.append(
        Participant(
            conversation_id=conv.id,
            kind=ParticipantKind.USER,
            subject_id=user_principal.subject_id,
            joined_at=conv.created_at,
        )
    )
    return uow, conv


@pytest.mark.asyncio
async def test_send_message_creates_message(user_principal, uow_with_conversation):
    uow, conv = uow_with_conversation
    client_msg_id = uuid.uuid4()

    msg, created = await message_service.send_message(
        conv.id, user_principal, client_msg_id, MessageType.TEXT, "hello", uow,
    )

    assert created is True
    assert msg.body == "hello"
    assert msg.conversation_id == conv.id
    assert msg.client_msg_id == client_msg_id
    assert uow._committed is True


@pytest.mark.asyncio
async def test_send_message_idempotent(user_principal, uow_with_conversation):
    uow, conv = uow_with_conversation
    client_msg_id = uuid.uuid4()

    msg1, created1 = await message_service.send_message(
        conv.id, user_principal, client_msg_id, MessageType.TEXT, "hello", uow,
    )
    uow._committed = False

    msg2, created2 = await message_service.send_message(
        conv.id, user_principal, client_msg_id, MessageType.TEXT, "hello", uow,
    )

    assert created1 is True
    assert created2 is False
    assert msg1.id == msg2.id
    assert uow._committed is False


@pytest.mark.asyncio
async def test_send_message_writes_outbox(user_principal, uow_with_conversation):
    uow, conv = uow_with_conversation

    await message_service.send_message(
        conv.id, user_principal, uuid.uuid4(), MessageType.TEXT, "test", uow,
    )

    assert len(uow.outbox._records) == 1
    assert uow.outbox._records[0]["event_type"] == "chat.message_created"


@pytest.mark.asyncio
async def test_send_message_forbidden_for_non_participant():
    """A regular user who is NOT a participant must be rejected."""
    from chat_service.application.dto.principal import Principal
    from chat_service.application.exceptions import ForbiddenError

    stranger = Principal(kind=ParticipantKind.USER, subject_id=999, roles=[])
    uow = FakeUoW()
    conv = make_conversation()
    uow.conversations._store[conv.id] = conv

    with pytest.raises(ForbiddenError):
        await message_service.send_message(
            conv.id, stranger, uuid.uuid4(), MessageType.TEXT, "hi", uow,
        )
