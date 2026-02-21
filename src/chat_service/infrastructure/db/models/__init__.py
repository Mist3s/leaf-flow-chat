"""Import all models so Alembic can discover them via Base.metadata."""
from chat_service.infrastructure.db.models.conversation import ConversationModel
from chat_service.infrastructure.db.models.message import MessageModel
from chat_service.infrastructure.db.models.outbox import OutboxMessageModel
from chat_service.infrastructure.db.models.participant import ParticipantModel
from chat_service.infrastructure.db.models.read_state import ReadStateModel

__all__ = [
    "ConversationModel",
    "MessageModel",
    "OutboxMessageModel",
    "ParticipantModel",
    "ReadStateModel",
]
