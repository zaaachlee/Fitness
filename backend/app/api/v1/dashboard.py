import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.meal import FoodLog, MealLog
from app.models.tracking import WaterLog, StepLog, SleepLog
from app.models.user import User, UserProfile, UserWeightLog
from app.models.workout import WorkoutLog, WorkoutSet

router = APIRouter()


# --- Pydantic Schemas ---

class TodayMacros(BaseModel):
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0


class TodayDashboardResponse(BaseModel):
    date: date
    calories_in: float = 0.0
    calories_target: Optional[int] = None
    macros: TodayMacros = TodayMacros()
    water_ml: int = 0
    water_target_ml: Optional[int] = None
    workout_minutes: int = 0
    workout_count: int = 0
    calories_out: float = 0.0
    current_weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    steps: int = 0
    sleep_minutes: int = 0


class TrendDataPoint(BaseModel):
    date: date
    value: float


class WeightTrendPoint(BaseModel):
    date: date
    weight_kg: float
    bmi: Optional[float] = None


class TrendsResponse(BaseModel):
    period: str
    avg_calories_per_day: float = 0.0
    avg_protein_per_day: float = 0.0
    avg_workouts_per_week: float = 0.0
    weight_curve: list[WeightTrendPoint] = []
    calorie_trend: list[TrendDataPoint] = []
    protein_trend: list[TrendDataPoint] = []
    workout_trend: list[TrendDataPoint] = []


# --- Helpers ---

def _calc_bmi(weight_kg: float, height_cm: Optional[float]) -> Optional[float]:
    """Calculate BMI from weight and height."""
    if height_cm and height_cm > 0:
        height_m = height_cm / 100.0
        return round(weight_kg / (height_m ** 2), 1)
    return None


def _get_period_dates(period: str) -> tuple[date, int]:
    """Get start date and number of days for a given period string."""
    today = date.today()
    if period == "7d":
        return today - timedelta(days=6), 7
    elif period == "30d":
        return today - timedelta(days=29), 30
    elif period == "90d":
        return today - timedelta(days=89), 90
    else:
        return today - timedelta(days=29), 30


# --- Endpoints ---

@router.get("/today", response_model=TodayDashboardResponse)
async def get_today_dashboard(
    target_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated data for a specific date (default today)."""
    today = target_date or date.today()

    # --- Calories in ---
    result = await db.execute(
        select(func.coalesce(func.sum(FoodLog.calories), 0.0))
        .join(MealLog)
        .where(MealLog.user_id == current_user.id, MealLog.date == today)
    )
    calories_in = round(result.scalar() or 0.0, 2)

    # --- Macros ---
    result = await db.execute(
        select(
            func.coalesce(func.sum(FoodLog.protein), 0.0),
            func.coalesce(func.sum(FoodLog.carbs), 0.0),
            func.coalesce(func.sum(FoodLog.fat), 0.0),
            func.coalesce(func.sum(FoodLog.fiber), 0.0),
        )
        .join(MealLog)
        .where(MealLog.user_id == current_user.id, MealLog.date == today)
    )
    macros_row = result.one_or_none()
    macros = TodayMacros(
        protein=round(macros_row[0] or 0.0, 2),
        carbs=round(macros_row[1] or 0.0, 2),
        fat=round(macros_row[2] or 0.0, 2),
        fiber=round(macros_row[3] or 0.0, 2),
    )
    macros.calories = calories_in

    # --- Water ---
    result = await db.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0))
        .where(WaterLog.user_id == current_user.id, WaterLog.date == today)
    )
    water_ml = result.scalar() or 0

    # --- Steps ---
    result = await db.execute(
        select(func.coalesce(func.sum(StepLog.steps), 0))
        .where(StepLog.user_id == current_user.id, StepLog.date == today)
    )
    steps = result.scalar() or 0

    # --- Sleep ---
    result = await db.execute(
        select(func.coalesce(func.sum(SleepLog.duration_minutes), 0))
        .where(SleepLog.user_id == current_user.id, SleepLog.date == today)
    )
    sleep_minutes = result.scalar() or 0

    # --- Workouts ---
    result = await db.execute(
        select(
            func.coalesce(func.count(WorkoutLog.id), 0),
            func.coalesce(func.sum(WorkoutLog.duration_minutes), 0),
            func.coalesce(func.sum(WorkoutLog.calories_burned), 0.0),
        ).where(WorkoutLog.user_id == current_user.id, WorkoutLog.date == today)
    )
    workout_row = result.one_or_none()
    workout_count = workout_row[0] or 0
    workout_minutes = workout_row[1] or 0
    calories_out = round(workout_row[2] or 0.0, 1)

    # --- Current weight ---
    result = await db.execute(
        select(UserWeightLog)
        .where(UserWeightLog.user_id == current_user.id)
        .order_by(UserWeightLog.date.desc())
        .limit(1)
    )
    latest_weight_log = result.scalar_one_or_none()
    current_weight = latest_weight_log.weight_kg if latest_weight_log else None
    bmi = _calc_bmi(current_weight, current_user.height_cm) if current_weight else None

    # --- Targets from profile ---
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    calories_target = profile.daily_calorie_target if profile else None
    water_target = profile.daily_water_target_ml if profile else None

    return TodayDashboardResponse(
        date=today,
        calories_in=calories_in,
        calories_target=calories_target,
        macros=macros,
        water_ml=water_ml,
        water_target_ml=water_target,
        workout_minutes=workout_minutes,
        workout_count=workout_count,
        calories_out=calories_out,
        current_weight_kg=current_weight,
        bmi=bmi,
        steps=steps,
        sleep_minutes=sleep_minutes,
    )


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trend data for the given period: average calories, protein, workouts, weight curve, BMI."""
    start_date, num_days = _get_period_dates(period)
    today = date.today()

    # --- Average calories per day ---
    result = await db.execute(
        select(func.coalesce(func.sum(FoodLog.calories), 0.0))
        .join(MealLog)
        .where(
            MealLog.user_id == current_user.id,
            MealLog.date >= start_date,
            MealLog.date <= today,
        )
    )
    total_calories = result.scalar() or 0.0
    avg_calories = round(total_calories / num_days, 2)

    # --- Average protein per day ---
    result = await db.execute(
        select(func.coalesce(func.sum(FoodLog.protein), 0.0))
        .join(MealLog)
        .where(
            MealLog.user_id == current_user.id,
            MealLog.date >= start_date,
            MealLog.date <= today,
        )
    )
    total_protein = result.scalar() or 0.0
    avg_protein = round(total_protein / num_days, 2)

    # --- Average workouts per week ---
    result = await db.execute(
        select(func.count(WorkoutLog.id))
        .where(
            WorkoutLog.user_id == current_user.id,
            WorkoutLog.date >= start_date,
            WorkoutLog.date <= today,
        )
    )
    total_workouts = result.scalar() or 0
    weeks = max(num_days / 7.0, 1.0)
    avg_workouts_per_week = round(total_workouts / weeks, 1)

    # --- Weight curve ---
    result = await db.execute(
        select(UserWeightLog)
        .where(
            UserWeightLog.user_id == current_user.id,
            UserWeightLog.date >= start_date,
            UserWeightLog.date <= today,
        )
        .order_by(UserWeightLog.date.asc())
    )
    weight_logs = result.scalars().all()
    weight_curve = [
        WeightTrendPoint(
            date=wl.date,
            weight_kg=wl.weight_kg,
            bmi=_calc_bmi(wl.weight_kg, current_user.height_cm),
        )
        for wl in weight_logs
    ]

    # --- Calorie trend (per day) ---
    result = await db.execute(
        select(MealLog.date, func.sum(FoodLog.calories))
        .join(FoodLog, MealLog.id == FoodLog.meal_log_id)
        .where(
            MealLog.user_id == current_user.id,
            MealLog.date >= start_date,
            MealLog.date <= today,
        )
        .group_by(MealLog.date)
        .order_by(MealLog.date.asc())
    )
    calorie_trend = [TrendDataPoint(date=row[0], value=round(row[1] or 0.0, 2)) for row in result.all()]

    # --- Protein trend (per day) ---
    result = await db.execute(
        select(MealLog.date, func.sum(FoodLog.protein))
        .join(FoodLog, MealLog.id == FoodLog.meal_log_id)
        .where(
            MealLog.user_id == current_user.id,
            MealLog.date >= start_date,
            MealLog.date <= today,
        )
        .group_by(MealLog.date)
        .order_by(MealLog.date.asc())
    )
    protein_trend = [TrendDataPoint(date=row[0], value=round(row[1] or 0.0, 2)) for row in result.all()]

    # --- Workout trend (per day) ---
    result = await db.execute(
        select(WorkoutLog.date, func.count(WorkoutLog.id))
        .where(
            WorkoutLog.user_id == current_user.id,
            WorkoutLog.date >= start_date,
            WorkoutLog.date <= today,
        )
        .group_by(WorkoutLog.date)
        .order_by(WorkoutLog.date.asc())
    )
    workout_trend = [TrendDataPoint(date=row[0], value=float(row[1] or 0)) for row in result.all()]

    return TrendsResponse(
        period=period,
        avg_calories_per_day=avg_calories,
        avg_protein_per_day=avg_protein,
        avg_workouts_per_week=avg_workouts_per_week,
        weight_curve=weight_curve,
        calorie_trend=calorie_trend,
        protein_trend=protein_trend,
        workout_trend=workout_trend,
    )
