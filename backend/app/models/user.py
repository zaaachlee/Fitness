import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Date, Float, Enum as SAEnum, ForeignKey, DateTime
from app.models.compat import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
import enum


class GoalEnum(str, enum.Enum):
    CUT = "cut"
    MAINTAIN = "maintain"
    BULK = "bulk"


class ActivityLevelEnum(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # AI settings per user
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Health metric visibility (JSONB: {"metric_id": true/false})
    health_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    weight_logs: Mapped[list["UserWeightLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    meal_logs: Mapped[list["MealLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    health_records: Mapped[list["HealthRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    water_logs: Mapped[list["WaterLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    step_logs: Mapped[list["StepLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sleep_logs: Mapped[list["SleepLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_messages: Mapped[list["AIChatMessage"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    workout_templates: Mapped[list["WorkoutTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    activity_level: Mapped[ActivityLevelEnum] = mapped_column(SAEnum(ActivityLevelEnum), default=ActivityLevelEnum.MODERATE)
    goal: Mapped[GoalEnum] = mapped_column(SAEnum(GoalEnum), default=GoalEnum.MAINTAIN)
    daily_calorie_target: Mapped[int | None] = mapped_column(nullable=True)
    daily_protein_target: Mapped[int | None] = mapped_column(nullable=True)
    daily_carbs_target: Mapped[int | None] = mapped_column(nullable=True)
    daily_fat_target: Mapped[int | None] = mapped_column(nullable=True)
    daily_water_target_ml: Mapped[int | None] = mapped_column(default=2000)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")


class UserWeightLog(Base):
    __tablename__ = "user_weight_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="weight_logs")
