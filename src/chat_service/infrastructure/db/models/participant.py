from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chat_service.infrastructure.db.base import Base


class ParticipantModel(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # user | admin
    subject_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    conversation = relationship("ConversationModel", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("conversation_id", "kind", "subject_id", name="uq_participant_member"),
        Index("ix_participants_subject", "kind", "subject_id", "conversation_id"),
    )
