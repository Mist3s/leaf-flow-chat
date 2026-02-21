from __future__ import annotations

import pytest

from chat_service.domain.value_objects.enums import ParticipantKind
from chat_service.services import conversation_service
from tests.conftest import FakeUoW, make_conversation


@pytest.mark.asyncio
async def test_get_or_create_creates_new(user_principal):
    uow = FakeUoW()

    conv = await conversation_service.get_or_create_support_conversation(
        user_principal.subject_id, uow,
    )

    assert conv is not None
    assert conv.topic_type == "support"
    assert conv.status == "open"
    assert uow._committed is True
    assert len(uow.participants._participants) == 1
    assert uow.participants._participants[0].kind == ParticipantKind.USER


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(user_principal):
    uow = FakeUoW()
    existing = make_conversation()
    uow.conversations._store[existing.id] = existing
    uow.conversations._user_convs[user_principal.subject_id] = [existing]

    conv = await conversation_service.get_or_create_support_conversation(
        user_principal.subject_id, uow,
    )

    assert conv.id == existing.id
    assert uow._committed is False


@pytest.mark.asyncio
async def test_list_user_conversations(user_principal):
    uow = FakeUoW()
    c1 = make_conversation()
    c2 = make_conversation()
    uow.conversations._user_convs[user_principal.subject_id] = [c1, c2]

    result = await conversation_service.list_user_conversations(
        user_principal, None, 20, uow,
    )

    assert len(result) == 2
