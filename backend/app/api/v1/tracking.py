"""
Tracking API — Water, Steps, Sleep logging endpoints.
"""
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.tracking import WaterLog, StepLog, SleepLog
from app.models.user import User

router = APIRouter()


# --- Schemas ---

class WaterLogResponse(BaseModel):
    id: uuid.UUID
    date: date
    amount_ml: int
    recorded_at: datetime
    class Config: from_attributes = True

class WaterLogCreate(BaseModel):
    amount_ml: int
    date: Optional[date] = None

class WaterTodayResponse(BaseModel):
    date: date
    total_ml: int
    logs: list[WaterLogResponse]

class StepLogResponse(BaseModel):
    id: uuid.UUID
    date: date
    steps: int
    source: Optional[str] = None
    class Config: from_attributes = True

class StepLogCreate(BaseModel):
    steps: int
    date: Optional[date] = None
    source: Optional[str] = None

class SleepLogResponse(BaseModel):
    id: uuid.UUID
    date: date
    duration_minutes: int
    quality: Optional[int] = None
    deep_sleep_minutes: Optional[int] = None
    rem_sleep_minutes: Optional[int] = None
    source: Optional[str] = None
    class Config: from_attributes = True

class SleepLogCreate(BaseModel):
    duration_minutes: int
    quality: Optional[int] = None
    deep_sleep_minutes: Optional[int] = None
    rem_sleep_minutes: Optional[int] = None
    date: Optional[date] = None
    source: Optional[str] = None


# --- Water ---

@router.get("/water", response_model=list[WaterLogResponse])
async def get_water_logs(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(WaterLog).where(WaterLog.user_id == current_user.id)
    if date_from: q = q.where(WaterLog.date >= date_from)
    if date_to: q = q.where(WaterLog.date <= date_to)
    q = q.order_by(WaterLog.date.desc(), WaterLog.recorded_at.desc()).limit(100)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/water/today", response_model=WaterTodayResponse)
async def get_today_water(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    result = await db.execute(
        select(WaterLog).where(WaterLog.user_id == current_user.id, WaterLog.date == today)
    )
    logs = result.scalars().all()
    total = sum(log.amount_ml for log in logs)
    return WaterTodayResponse(date=today, total_ml=total, logs=logs)


@router.post("/water", response_model=WaterLogResponse, status_code=201)
async def log_water(
    body: WaterLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    log = WaterLog(id=uuid.uuid4(), user_id=current_user.id, date=body.date or date.today(), amount_ml=body.amount_ml)
    db.add(log)
    await db.flush()
    await db.commit()
    return log


# --- Steps ---

@router.get("/steps", response_model=list[StepLogResponse])
async def get_step_logs(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(StepLog).where(StepLog.user_id == current_user.id)
    if date_from: q = q.where(StepLog.date >= date_from)
    if date_to: q = q.where(StepLog.date <= date_to)
    q = q.order_by(StepLog.date.desc()).limit(100)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/steps", response_model=StepLogResponse, status_code=201)
async def log_steps(
    body: StepLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    log = StepLog(id=uuid.uuid4(), user_id=current_user.id, date=body.date or date.today(), steps=body.steps, source=body.source)
    db.add(log)
    await db.flush()
    await db.commit()
    return log


# --- Sleep ---

@router.get("/sleep", response_model=list[SleepLogResponse])
async def get_sleep_logs(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(SleepLog).where(SleepLog.user_id == current_user.id)
    if date_from: q = q.where(SleepLog.date >= date_from)
    if date_to: q = q.where(SleepLog.date <= date_to)
    q = q.order_by(SleepLog.date.desc()).limit(100)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/sleep", response_model=SleepLogResponse, status_code=201)
async def log_sleep(
    body: SleepLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    log = SleepLog(id=uuid.uuid4(), user_id=current_user.id, date=body.date or date.today(),
                   duration_minutes=body.duration_minutes, quality=body.quality,
                   deep_sleep_minutes=body.deep_sleep_minutes, rem_sleep_minutes=body.rem_sleep_minutes, source=body.source)
    db.add(log)
    await db.flush()
    await db.commit()
    return log
