from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from chat_service.api.deps import CurrentPrincipal, UoWDep
from chat_service.api.v1.schemas.conversation import ConversationResponse
from chat_service.services import conversation_service

router = APIRouter(prefix="/api/v1/chat/conversations", tags=["conversations"])


@router.post("/support", response_model=ConversationResponse)
async def create_support_conversation(
    principal: CurrentPrincipal,
    uow: UoWDep,
) -> ConversationResponse:
    conv = await conversation_service.get_or_create_support_conversation(
        principal.subject_id, uow,
    )
    return ConversationResponse.model_validate(conv, from_attributes=True)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    principal: CurrentPrincipal,
    uow: UoWDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[ConversationResponse]:
    convs = await conversation_service.list_user_conversations(
        principal, cursor, limit, uow,
    )
    return [ConversationResponse.model_validate(c, from_attributes=True) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    principal: CurrentPrincipal,
    uow: UoWDep,
) -> ConversationResponse:
    conv = await conversation_service.get_conversation(conversation_id, principal, uow)
    return ConversationResponse.model_validate(conv, from_attributes=True)
