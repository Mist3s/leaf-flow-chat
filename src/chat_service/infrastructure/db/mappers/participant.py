from __future__ import annotations

from chat_service.domain.entities.participant import Participant
from chat_service.infrastructure.db.models.participant import ParticipantModel


def model_to_entity(model: ParticipantModel) -> Participant:
    return Participant(
        conversation_id=model.conversation_id,
        kind=model.kind,
        subject_id=model.subject_id,
        joined_at=model.joined_at,
    )


def entity_to_model(entity: Participant) -> ParticipantModel:
    return ParticipantModel(
        conversation_id=entity.conversation_id,
        kind=entity.kind,
        subject_id=entity.subject_id,
        joined_at=entity.joined_at,
    )
