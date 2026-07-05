import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, Enum as SAEnum, ForeignKey, DateTime
from app.models.compat import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
import enum


class ExerciseTypeEnum(str, enum.Enum):
    COMPOUND = "compound"
    ISOLATION = "isolation"
    BODYWEIGHT = "bodyweight"
    CARDIO = "cardio"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    primary_muscle: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # chest, back, legs, shoulders, arms, core
    secondary_muscles: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # ["triceps", "front_delts"]
    equipment: Mapped[str | None] = mapped_column(String(100), nullable=True)  # barbell, dumbbell, cable, machine, bodyweight
    exercise_type: Mapped[ExerciseTypeEnum] = mapped_column(SAEnum(ExerciseTypeEnum), default=ExerciseTypeEnum.COMPOUND)
    met_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # Metabolic Equivalent of Task
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    instructions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # ["step 1", "step 2", ...]
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
