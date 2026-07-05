import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey
from app.models.compat import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aliases: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # ["鸡胸", "鸡胸脯", "chicken breast"]
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # meat, vegetable, fruit, grain, dairy, snack, beverage, etc.

    # Macronutrients (per 100g)
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, default=0)
    carbs_per_100g: Mapped[float] = mapped_column(Float, default=0)
    fat_per_100g: Mapped[float] = mapped_column(Float, default=0)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    cholesterol_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    saturated_fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    trans_fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Advanced nutrition
    gi: Mapped[float | None] = mapped_column(Float, nullable=True)  # Glycemic Index
    gl: Mapped[float | None] = mapped_column(Float, nullable=True)  # Glycemic Load
    purine_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Vitamins and Minerals as flexible JSONB
    vitamins: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {"A": 0, "C": 2.5, "D": 0, ...}
    minerals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {"calcium": 12, "iron": 0.5, ...}

    # Metadata
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
