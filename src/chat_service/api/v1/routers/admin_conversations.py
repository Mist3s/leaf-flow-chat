from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from chat_service.api.deps import CurrentAdmin, UoWDep
from chat_service.api.v1.schemas.admin import AdminConversationFilters, PatchConversationRequest
from chat_service.api.v1.schemas.conversation import ConversationResponse
from chat_service.api.v1.schemas.message import MessageResponse, SendMessageRequest
from chat_service.application.dto.conversation import ConversationFilterDTO
from chat_service.domain.value_objects.enums import ConversationStatus
from chat_service.services import admin_service, message_service

router = APIRouter(prefix="/api/v1/chat/admin/conversations", tags=["admin"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    admin: CurrentAdmin,
    uow: UoWDep,
    status: ConversationStatus | None = Query(None),
    assignee_admin_id: int | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[ConversationResponse]:
    filters = ConversationFilterDTO(
        status=status,
        assignee_admin_id=assignee_admin_id,
        cursor=cursor,
        limit=limit,
    )
    convs = await admin_service.list_conversations(filters, uow)
    return [ConversationResponse.model_validate(c, from_attributes=True) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    admin: CurrentAdmin,
    uow: UoWDep,
) -> ConversationResponse:
    conv = await admin_service.get_conversation(conversation_id, uow)
    return ConversationResponse.model_validate(conv, from_attributes=True)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def patch_conversation(
    conversation_id: UUID,
    body: PatchConversationRequest,
    admin: CurrentAdmin,
    uow: UoWDep,
) -> ConversationResponse:
    if body.status == ConversationStatus.CLOSED:
        conv = await admin_service.close_conversation(conversation_id, admin, uow)
    elif body.assignee_admin_id is not None:
        conv = await admin_service.assign_conversation(
            conversation_id, body.assignee_admin_id, admin, uow,
        )
    else:
        conv = await admin_service.get_conversation(conversation_id, uow)
    return ConversationResponse.model_validate(conv, from_attributes=True)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    admin: CurrentAdmin,
    uow: UoWDep,
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[MessageResponse]:
    messages = await message_service.list_messages(
        conversation_id, admin, cursor, limit, uow,
    )
    return [MessageResponse.model_validate(m, from_attributes=True) for m in messages]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    admin: CurrentAdmin,
    uow: UoWDep,
) -> MessageResponse:
    msg, _created = await message_service.send_message(
        conversation_id,
        admin,
        body.client_msg_id,
        body.type,
        body.body,
        uow,
    )
    return MessageResponse.model_validate(msg, from_attributes=True)
