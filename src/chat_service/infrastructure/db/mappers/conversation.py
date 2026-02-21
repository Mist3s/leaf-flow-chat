from __future__ import annotations

from chat_service.domain.entities.conversation import Conversation
from chat_service.infrastructure.db.models.conversation import ConversationModel


def model_to_entity(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        topic_type=model.topic_type,
        topic_id=model.topic_id,
        status=model.status,
        assignee_admin_id=model.assignee_admin_id,
        last_message_at=model.last_message_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def entity_to_model(entity: Conversation) -> ConversationModel:
    return ConversationModel(
        id=entity.id,
        topic_type=entity.topic_type,
        topic_id=entity.topic_id,
        status=entity.status,
        assignee_admin_id=entity.assignee_admin_id,
        last_message_at=entity.last_message_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
