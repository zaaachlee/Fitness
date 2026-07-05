import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Enum as SAEnum, DateTime
from app.models.compat import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
import enum


class KnowledgeCategoryEnum(str, enum.Enum):
    SPORTS_NUTRITION = "sports_nutrition"
    FITNESS_TRAINING = "fitness_training"
    HEALTH = "health"


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[KnowledgeCategoryEnum] = mapped_column(SAEnum(KnowledgeCategoryEnum), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # ["protein", "muscle_gain", "recovery"]
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Reserved for future vector embedding
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
