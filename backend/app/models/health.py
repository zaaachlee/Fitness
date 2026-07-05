import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, Float, Enum as SAEnum, ForeignKey, DateTime, Date
from app.models.compat import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
import enum


class HealthCategoryEnum(str, enum.Enum):
    LIPID = "lipid"           # 血脂
    LIVER = "liver"           # 肝功能
    KIDNEY = "kidney"         # 肾功能
    BLOOD_SUGAR = "blood_sugar"  # 血糖
    URIC_ACID = "uric_acid"   # 尿酸
    VITAMIN = "vitamin"       # 维生素
    BODY_COMP = "body_comp"   # 身体成分
    OTHER = "other"


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    normal_range_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_range_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[HealthCategoryEnum] = mapped_column(SAEnum(HealthCategoryEnum), nullable=False)
    clinical_significance: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    abnormal_risk: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    dietary_advice: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    exercise_advice: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reference_source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_metrics.id", ondelete="RESTRICT"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="health_records")
    metric: Mapped["HealthMetric"] = relationship()
