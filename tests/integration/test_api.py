"""Integration smoke tests for REST API (using mocked UoW via dependency override)."""
from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from chat_service.api.deps import get_uow
from chat_service.app import create_app
from chat_service.config import settings
from tests.conftest import FakeUoW, make_conversation, make_message

from chat_service.domain.entities.participant import Participant
from chat_service.domain.value_objects.enums import ParticipantKind


def _make_token(sub: int = 42, kind: str = "user", roles: list | None = None) -> str:
    return jwt.encode(
        {"sub": str(sub), "kind": kind, "roles": roles or []},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture
def app_with_uow():
    app = create_app()
    uow = FakeUoW()

    async def _override():
        yield uow

    app.dependency_overrides[get_uow] = _override
    return app, uow


@pytest.fixture
def client(app_with_uow):
    app, _ = app_with_uow
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def uow(app_with_uow):
    _, uow = app_with_uow
    return uow


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_support_conversation(client, uow):
    token = _make_token()
    resp = client.post(
        "/api/v1/chat/conversations/support",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic_type"] == "support"
    assert data["status"] == "open"


def test_list_conversations_empty(client):
    token = _make_token()
    resp = client.get(
        "/api/v1/chat/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_send_message(client, uow):
    conv = make_conversation()
    uow.conversations._store[conv.id] = conv
    uow.participants._participants.append(
        Participant(
            conversation_id=conv.id,
            kind=ParticipantKind.USER,
            subject_id=42,
            joined_at=conv.created_at,
        )
    )

    token = _make_token()
    resp = client.post(
        f"/api/v1/chat/conversations/{conv.id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "client_msg_id": str(uuid.uuid4()),
            "type": "text",
            "body": "hello world",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "hello world"
    assert data["sender_kind"] == "user"


def test_admin_list_conversations(client, uow):
    conv = make_conversation()
    uow.conversations._store[conv.id] = conv

    token = _make_token(sub=1, kind="admin", roles=["admin"])
    resp = client.get(
        "/api/v1/chat/admin/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_unauthorized_returns_error(client):
    resp = client.post("/api/v1/chat/conversations/support")
    assert resp.status_code in (401, 403)


def test_user_cannot_access_admin(client):
    token = _make_token(sub=42, kind="user")
    resp = client.get(
        "/api/v1/chat/admin/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
