import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.health import HealthCategoryEnum, HealthMetric, HealthRecord
from app.models.user import User

router = APIRouter()


# --- Pydantic Schemas ---

class HealthMetricResponse(BaseModel):
    id: uuid.UUID
    name: str
    name_en: Optional[str] = None
    unit: str
    normal_range_min: Optional[float] = None
    normal_range_max: Optional[float] = None
    category: HealthCategoryEnum
    clinical_significance: Optional[str] = None

    class Config:
        from_attributes = True


class HealthRecordCreateRequest(BaseModel):
    date: date
    metric_id: uuid.UUID
    value: float
    notes: Optional[str] = None


class HealthRecordUpdateRequest(BaseModel):
    date: Optional[date] = None
    value: Optional[float] = None
    notes: Optional[str] = None


class HealthRecordResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    metric_id: uuid.UUID
    value: float
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HealthRecordWithMetricResponse(BaseModel):
    id: uuid.UUID
    date: date
    value: float
    notes: Optional[str] = None
    created_at: datetime
    metric: HealthMetricResponse

    class Config:
        from_attributes = True


class HealthRecordListResponse(BaseModel):
    records: list[HealthRecordWithMetricResponse]
    total: int


class TrendDataPoint(BaseModel):
    date: date
    value: float
    in_range: bool


class MetricTrendResponse(BaseModel):
    metric_id: uuid.UUID
    metric_name: str
    unit: str
    normal_range_min: Optional[float] = None
    normal_range_max: Optional[float] = None
    data_points: list[TrendDataPoint]


# --- Endpoints ---

@router.get("/metrics", response_model=list[HealthMetricResponse])
async def list_health_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all health metric definitions."""
    result = await db.execute(select(HealthMetric).order_by(HealthMetric.category, HealthMetric.name))
    metrics = result.scalars().all()
    return metrics


@router.get("/records", response_model=HealthRecordListResponse)
async def list_health_records(
    metric_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List health records with optional filters."""
    query = (
        select(HealthRecord)
        .where(HealthRecord.user_id == current_user.id)
        .options(selectinload(HealthRecord.metric))
        .order_by(HealthRecord.date.desc())
    )
    if metric_id:
        query = query.where(HealthRecord.metric_id == metric_id)
    if date_from:
        query = query.where(HealthRecord.date >= date_from)
    if date_to:
        query = query.where(HealthRecord.date <= date_to)

    query = query.limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return HealthRecordListResponse(records=records, total=len(records))


@router.post("/records", response_model=HealthRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_health_record(
    body: HealthRecordCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new health record."""
    # Verify metric exists
    result = await db.execute(select(HealthMetric).where(HealthMetric.id == body.metric_id))
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=404, detail="Health metric not found")

    record = HealthRecord(
        user_id=current_user.id,
        date=body.date,
        metric_id=body.metric_id,
        value=body.value,
        notes=body.notes,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    await db.commit()
    return record


@router.put("/records/{record_id}", response_model=HealthRecordResponse)
async def update_health_record(
    record_id: uuid.UUID,
    body: HealthRecordUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HealthRecord).where(HealthRecord.id == record_id, HealthRecord.user_id == current_user.id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Health record not found")
    if body.value is not None: record.value = body.value
    if body.date is not None: record.date = body.date
    if body.notes is not None: record.notes = body.notes
    await db.flush()
    await db.commit()
    return record


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_record(
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HealthRecord).where(HealthRecord.id == record_id, HealthRecord.user_id == current_user.id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Health record not found")
    await db.delete(record)
    await db.commit()


@router.get("/{metric_id}/trend", response_model=MetricTrendResponse)
async def get_metric_trend(
    metric_id: uuid.UUID,
    limit: int = Query(default=90, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trend data for a specific health metric."""
    result = await db.execute(select(HealthMetric).where(HealthMetric.id == metric_id))
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=404, detail="Health metric not found")

    result = await db.execute(
        select(HealthRecord)
        .where(
            HealthRecord.user_id == current_user.id,
            HealthRecord.metric_id == metric_id,
        )
        .order_by(HealthRecord.date.asc())
        .limit(limit)
    )
    records = result.scalars().all()

    data_points = []
    for r in records:
        in_range = True
        if metric.normal_range_min is not None and r.value < metric.normal_range_min:
            in_range = False
        if metric.normal_range_max is not None and r.value > metric.normal_range_max:
            in_range = False
        data_points.append(TrendDataPoint(date=r.date, value=r.value, in_range=in_range))

    return MetricTrendResponse(
        metric_id=metric.id,
        metric_name=metric.name,
        unit=metric.unit,
        normal_range_min=metric.normal_range_min,
        normal_range_max=metric.normal_range_max,
        data_points=data_points,
    )
