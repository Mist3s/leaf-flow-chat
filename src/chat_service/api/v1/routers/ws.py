from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from chat_service.api.deps import get_verifier
from chat_service.application.dto.principal import Principal
from chat_service.config import settings
from chat_service.infrastructure.db.session import AsyncSessionLocal
from chat_service.infrastructure.db.uow import SqlAlchemyUoW
from chat_service.infrastructure.ws.manager import ConnectionManager
from chat_service.infrastructure.ws.protocol import WsInbound, WsOutbound
from chat_service.services import message_service, read_state_service
from chat_service.domain.value_objects.enums import MessageType

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    return manager


async def _authenticate(token: str) -> Principal | None:
    try:
        verifier = get_verifier()
        return await verifier.verify(token)
    except Exception:
        logger.debug("WS auth failed", exc_info=True)
        return None


@router.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    principal = await _authenticate(token)
    if principal is None:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    pkey = principal.principal_key
    await manager.connect(websocket, pkey)

    heartbeat_task = asyncio.create_task(
        _heartbeat(websocket), name=f"ws-heartbeat-{pkey}",
    )
    try:
        await _read_loop(websocket, principal)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS error for %s", pkey)
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket, pkey)


async def _heartbeat(ws: WebSocket) -> None:
    interval = settings.WS_HEARTBEAT_SECONDS
    try:
        while True:
            await asyncio.sleep(interval)
            await ws.send_text(WsOutbound(type="pong", data={}).model_dump_json())
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


async def _read_loop(ws: WebSocket, principal: Principal) -> None:
    pkey = principal.principal_key
    while True:
        raw = await ws.receive_text()
        try:
            msg = WsInbound.model_validate_json(raw)
        except Exception:
            await ws.send_text(
                WsOutbound(type="error", data={"code": "invalid_payload"}).model_dump_json()
            )
            continue

        if msg.type == "ping":
            await ws.send_text(WsOutbound(type="pong", data={}).model_dump_json())

        elif msg.type == "subscribe":
            conversation_id = msg.data.get("conversation_id")
            if conversation_id:
                manager.subscribe(pkey, UUID(conversation_id))

        elif msg.type == "message.send":
            await _handle_send(ws, principal, msg.data)

        elif msg.type == "mark_read":
            await _handle_mark_read(principal, msg.data)

        else:
            await ws.send_text(
                WsOutbound(type="error", data={"code": "unknown_type", "type": msg.type}).model_dump_json()
            )


async def _handle_send(ws: WebSocket, principal: Principal, data: dict) -> None:
    try:
        conversation_id = UUID(data["conversation_id"])
        client_msg_id = UUID(data["client_msg_id"])
        body = data.get("body")
        msg_type = MessageType(data.get("type", "text"))
    except (KeyError, ValueError) as exc:
        await ws.send_text(
            WsOutbound(type="error", data={"code": "invalid_data", "detail": str(exc)}).model_dump_json()
        )
        return

    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        try:
            msg, created = await message_service.send_message(
                conversation_id, principal, client_msg_id, msg_type, body, uow,
            )
        except Exception as exc:
            await ws.send_text(
                WsOutbound(type="error", data={"code": "send_failed", "detail": str(exc)}).model_dump_json()
            )
            return

    msg_data = {
        "conversation_id": str(msg.conversation_id),
        "message": {
            "id": str(msg.id),
            "conversation_id": str(msg.conversation_id),
            "sender_kind": msg.sender_kind,
            "sender_id": msg.sender_id,
            "type": msg.type,
            "body": msg.body,
            "client_msg_id": str(msg.client_msg_id),
            "created_at": msg.created_at.isoformat(),
        },
    }
    await manager.broadcast_to_conversation(conversation_id, "message.created", msg_data)


async def _handle_mark_read(principal: Principal, data: dict) -> None:
    try:
        conversation_id = UUID(data["conversation_id"])
        last_message_id = UUID(data["last_message_id"])
    except (KeyError, ValueError):
        return

    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        try:
            await read_state_service.mark_read(
                conversation_id, principal, last_message_id, uow,
            )
        except Exception:
            logger.exception("mark_read failed")
