from __future__ import annotations

from chat_service.domain.entities.message import Message
from chat_service.infrastructure.db.models.message import MessageModel


def model_to_entity(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        conversation_id=model.conversation_id,
        sender_kind=model.sender_kind,
        sender_id=model.sender_id,
        type=model.type,
        body=model.body,
        payload=model.payload,
        client_msg_id=model.client_msg_id,
        created_at=model.created_at,
    )


def entity_to_model(entity: Message) -> MessageModel:
    return MessageModel(
        id=entity.id,
        conversation_id=entity.conversation_id,
        sender_kind=entity.sender_kind,
        sender_id=entity.sender_id,
        type=entity.type,
        body=entity.body,
        payload=entity.payload,
        client_msg_id=entity.client_msg_id,
        created_at=entity.created_at,
    )
