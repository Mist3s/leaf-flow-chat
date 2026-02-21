from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chat_service.infrastructure.db.base import Base


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    topic_type: Mapped[str] = mapped_column(String(50), nullable=False, default="support")
    topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    assignee_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    # relationships
    participants = relationship("ParticipantModel", back_populates="conversation", lazy="selectin")
    messages = relationship("MessageModel", back_populates="conversation", lazy="noload")

    __table_args__ = (
        Index("ix_conversations_status_last_message", "status", last_message_at.desc()),
        Index("ix_conversations_topic", "topic_type", "topic_id"),
    )
