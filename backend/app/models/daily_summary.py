import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.compat import UUID

from app.core.database import Base


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Diet
    calories_in: Mapped[float] = mapped_column(Float, default=0)
    protein_grams: Mapped[float] = mapped_column(Float, default=0)
    carbs_grams: Mapped[float] = mapped_column(Float, default=0)
    fat_grams: Mapped[float] = mapped_column(Float, default=0)
    water_ml: Mapped[int] = mapped_column(Integer, default=0)

    # Workout
    workout_count: Mapped[int] = mapped_column(Integer, default=0)
    workout_volume: Mapped[float] = mapped_column(Float, default=0)
    workout_calories: Mapped[float] = mapped_column(Float, default=0)
    workout_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Sleep
    sleep_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Body
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Health
    health_records_count: Mapped[int] = mapped_column(Integer, default=0)
    health_abnormal_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
