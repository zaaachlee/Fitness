import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Enum as SAEnum, ForeignKey, DateTime
from app.models.compat import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
import enum


class ChatRoleEnum(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[ChatRoleEnum] = mapped_column(SAEnum(ChatRoleEnum), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    context_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # diet, workout, health, general
    context_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Data snapshot used for this response
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="chat_messages")
