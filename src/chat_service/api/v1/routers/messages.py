from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from chat_service.api.deps import CurrentPrincipal, UoWDep
from chat_service.api.v1.schemas.message import MessageResponse, SendMessageRequest
from chat_service.services import message_service

router = APIRouter(prefix="/api/v1/chat/conversations", tags=["messages"])


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    principal: CurrentPrincipal,
    uow: UoWDep,
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[MessageResponse]:
    messages = await message_service.list_messages(
        conversation_id, principal, cursor, limit, uow,
    )
    return [MessageResponse.model_validate(m, from_attributes=True) for m in messages]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    principal: CurrentPrincipal,
    uow: UoWDep,
) -> MessageResponse:
    msg, _created = await message_service.send_message(
        conversation_id,
        principal,
        body.client_msg_id,
        body.type,
        body.body,
        uow,
    )
    return MessageResponse.model_validate(msg, from_attributes=True)
