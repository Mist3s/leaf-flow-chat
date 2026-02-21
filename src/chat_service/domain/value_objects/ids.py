from __future__ import annotations

from typing import NewType
from uuid import UUID

ConversationId = NewType("ConversationId", UUID)
MessageId = NewType("MessageId", UUID)
SubjectId = NewType("SubjectId", int)
