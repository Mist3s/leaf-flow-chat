from __future__ import annotations

import uuid

import pytest

from chat_service.application.exceptions import ForbiddenError, NotFoundError
from chat_service.domain.entities.participant import Participant
from chat_service.domain.value_objects.enums import ConversationStatus, ParticipantKind
from chat_service.services import admin_service
from tests.conftest import FakeUoW, make_conversation


@pytest.fixture
def uow_with_conversation():
    uow = FakeUoW()
    conv = make_conversation()
    uow.conversations._store[conv.id] = conv
    return uow, conv


@pytest.mark.asyncio
async def test_assign_conversation(admin_principal, uow_with_conversation):
    uow, conv = uow_with_conversation

    result = await admin_service.assign_conversation(
        conv.id, admin_principal.subject_id, admin_principal, uow,
    )

    assert result is not None
    assert uow._committed is True
    assert any(r["event_type"] == "chat.conversation_updated" for r in uow.outbox._records)


@pytest.mark.asyncio
async def test_assign_conversation_forbidden_for_user(user_principal, uow_with_conversation):
    uow, conv = uow_with_conversation

    with pytest.raises(ForbiddenError):
        await admin_service.assign_conversation(
            conv.id, 1, user_principal, uow,
        )


@pytest.mark.asyncio
async def test_close_conversation(admin_principal, uow_with_conversation):
    uow, conv = uow_with_conversation

    result = await admin_service.close_conversation(conv.id, admin_principal, uow)

    assert result is not None
    assert uow._committed is True
    assert any(r["event_type"] == "chat.conversation_updated" for r in uow.outbox._records)


@pytest.mark.asyncio
async def test_close_nonexistent_conversation(admin_principal):
    uow = FakeUoW()

    with pytest.raises(NotFoundError):
        await admin_service.close_conversation(uuid.uuid4(), admin_principal, uow)
