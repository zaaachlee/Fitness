import json
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User, UserWeightLog
from app.models.meal import MealLog, FoodLog
from app.models.workout import WorkoutLog
from app.models.tracking import SleepLog
from app.models.health import HealthRecord, HealthMetric
from app.models.daily_summary import DailySummary
from app.models.weekly_report import WeeklyReport
from app.services import ai_service

router = APIRouter()


# --- Schemas ---

class DailySummaryResponse(BaseModel):
    id: str
    date: date
    calories_in: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    water_ml: int
    workout_count: int
    workout_volume: float
    workout_calories: float
    workout_minutes: int
    sleep_minutes: int
    sleep_quality: Optional[int] = None
    weight_kg: Optional[float] = None
    health_records_count: int
    health_abnormal_count: int
    class Config: from_attributes = True


class WeeklyReportResponse(BaseModel):
    id: str
    week_start: date
    content: str
    created_at: str


class WeeklyReportListResponse(BaseModel):
    reports: list[WeeklyReportResponse]


def _get_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


async def _generate_daily_summary(user_id: uuid.UUID, target_date: date, db: AsyncSession) -> DailySummary:
    # Check existing
    result = await db.execute(
        select(DailySummary).where(DailySummary.user_id == user_id, DailySummary.date == target_date)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Diet
    meal_result = await db.execute(
        select(
            func.coalesce(func.sum(FoodLog.calories), 0.0),
            func.coalesce(func.sum(FoodLog.protein), 0.0),
            func.coalesce(func.sum(FoodLog.carbs), 0.0),
            func.coalesce(func.sum(FoodLog.fat), 0.0),
        ).join(MealLog).where(MealLog.user_id == user_id, MealLog.date == target_date)
    )
    diet = meal_result.one()

    # Water (simplified)
    water_result = await db.execute(
        select(func.coalesce(func.sum(FoodLog.water_ml if hasattr(FoodLog, 'water_ml') else 0), 0))
    )
    water_ml = 0  # Simplified

    # Workout
    wo_result = await db.execute(
        select(
            func.coalesce(func.count(WorkoutLog.id), 0),
            func.coalesce(func.sum(WorkoutLog.calories_burned), 0.0),
            func.coalesce(func.sum(WorkoutLog.duration_minutes), 0),
        ).where(WorkoutLog.user_id == user_id, WorkoutLog.date == target_date)
    )
    wo = wo_result.one()
    # Calculate volume from sets
    from app.models.workout import WorkoutSet
    volume_result = await db.execute(
        select(func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0.0))
        .join(WorkoutLog).where(WorkoutLog.user_id == user_id, WorkoutLog.date == target_date)
    )
    workout_volume = volume_result.scalar() or 0.0

    # Sleep
    sleep_result = await db.execute(
        select(
            func.coalesce(func.sum(SleepLog.duration_minutes), 0),
            func.coalesce(func.avg(SleepLog.quality), None),
        ).where(SleepLog.user_id == user_id, SleepLog.date == target_date)
    )
    sleep = sleep_result.one()

    # Weight
    wt_result = await db.execute(
        select(UserWeightLog.weight_kg)
        .where(UserWeightLog.user_id == user_id, UserWeightLog.date <= target_date)
        .order_by(UserWeightLog.date.desc()).limit(1)
    )
    weight_kg = wt_result.scalar()

    # Health
    hr_count_result = await db.execute(
        select(func.count(HealthRecord.id))
        .where(HealthRecord.user_id == user_id, HealthRecord.date == target_date)
    )
    health_records_count = hr_count_result.scalar() or 0

    abnormal = 0
    if health_records_count > 0:
        records_result = await db.execute(
            select(HealthRecord, HealthMetric)
            .join(HealthMetric, HealthRecord.metric_id == HealthMetric.id)
            .where(HealthRecord.user_id == user_id, HealthRecord.date == target_date)
        )
        for rec, metric in records_result:
            if metric.normal_range_min is not None and rec.value < metric.normal_range_min:
                abnormal += 1
            elif metric.normal_range_max is not None and rec.value > metric.normal_range_max:
                abnormal += 1

    summary = DailySummary(
        user_id=user_id, date=target_date,
        calories_in=round(diet[0], 1), protein_grams=round(diet[1], 1),
        carbs_grams=round(diet[2], 1), fat_grams=round(diet[3], 1),
        water_ml=water_ml,
        workout_count=int(wo[0]), workout_volume=round(workout_volume, 1),
        workout_calories=round(wo[1], 1), workout_minutes=int(wo[2] or 0),
        sleep_minutes=int(sleep[0] or 0),
        sleep_quality=round(sleep[1]) if sleep[1] else None,
        weight_kg=weight_kg,
        health_records_count=int(health_records_count), health_abnormal_count=abnormal,
    )
    db.add(summary)
    await db.flush()
    await db.commit()
    return summary


WEEKLY_REPORT_PROMPT = """你是专业的AI私人健身教练。根据用户上周的每日数据摘要，生成一份详细的周报。

数据包括：每日热量摄入、三大营养素（蛋白质/碳水/脂肪）、饮水量、训练次数/容量/消耗/时长、睡眠时长/质量、体重、健康指标变化。

请严格按照以下JSON格式返回（不要包含额外文字）：

{
  "overview": "上周基本情况概述（2-3句话）",
  "diet_assessment": "饮食评估：热量/蛋白/碳水/脂肪是否达标，具体数据和目标对比",
  "workout_assessment": "训练评估：训练频率/容量/消耗是否合理",
  "sleep_assessment": "睡眠评估：时长和质量分析",
  "weight_trend": "体重变化趋势分析",
  "health_notes": "健康指标：异常项提醒",
  "improvements": "需要改进的地方（3-5条具体可操作建议，每条一行）",
  "next_week_plan": "下周具体建议（饮食/训练/睡眠的具体目标）"
}

用中文输出。数据要具体，建议要可操作。"""


@router.get("/daily-summary")
async def get_daily_summary(
    target_date: date = Query(alias="date"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    summary = await _generate_daily_summary(current_user.id, target_date, db)
    return {
        "id": str(summary.id), "date": summary.date,
        "calories_in": summary.calories_in, "protein_grams": summary.protein_grams,
        "carbs_grams": summary.carbs_grams, "fat_grams": summary.fat_grams,
        "water_ml": summary.water_ml,
        "workout_count": summary.workout_count, "workout_volume": summary.workout_volume,
        "workout_calories": summary.workout_calories, "workout_minutes": summary.workout_minutes,
        "sleep_minutes": summary.sleep_minutes, "sleep_quality": summary.sleep_quality,
        "weight_kg": summary.weight_kg,
        "health_records_count": summary.health_records_count,
        "health_abnormal_count": summary.health_abnormal_count,
    }


@router.get("/weekly")
async def get_weekly_report(
    week_start: date = Query(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.user_id == current_user.id, WeeklyReport.week_start == week_start
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="周报尚未生成")
    return {"id": str(report.id), "week_start": report.week_start, "content": report.content, "created_at": report.created_at.isoformat()}


@router.post("/weekly")
async def generate_weekly_report(
    week_start: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    start = week_start or _get_monday(today) - timedelta(days=7)

    # Check existing
    result = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.user_id == current_user.id, WeeklyReport.week_start == start
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该周周报已生成")

    # Generate daily summaries for past 7 days
    summaries = []
    for i in range(7):
        d = start + timedelta(days=i)
        summary = await _generate_daily_summary(current_user.id, d, db)
        summaries.append({
            "date": str(summary.date),
            "calories_in": summary.calories_in, "protein": summary.protein_grams,
            "carbs": summary.carbs_grams, "fat": summary.fat_grams,
            "water_ml": summary.water_ml,
            "workouts": summary.workout_count, "volume": summary.workout_volume,
            "calories_burned": summary.workout_calories, "minutes": summary.workout_minutes,
            "sleep_min": summary.sleep_minutes, "sleep_quality": summary.sleep_quality,
            "weight": summary.weight_kg,
            "health_records": summary.health_records_count, "health_abnormal": summary.health_abnormal_count,
        })

    # Get weight history for trend
    wt_result = await db.execute(
        select(UserWeightLog).where(
            UserWeightLog.user_id == current_user.id,
            UserWeightLog.date >= start - timedelta(days=7), UserWeightLog.date <= start + timedelta(days=6)
        ).order_by(UserWeightLog.date.asc())
    )
    weight_logs = [{"date": str(w.date), "weight": w.weight_kg} for w in wt_result.scalars().all()]

    user_data = json.dumps({"summaries": summaries, "weight_history": weight_logs}, ensure_ascii=False)

    try:
        content = await ai_service._call_llm_for_user(
            WEEKLY_REPORT_PROMPT, user_data, user=current_user, temperature=0.7, max_tokens=3000
        )
        parsed = json.loads(content.strip()) if content.strip().startswith("{") else {"overview": content}
        report_text = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        report_text = "AI 周报生成失败，请检查 API Key 配置后重试。"

    report = WeeklyReport(user_id=current_user.id, week_start=start, content=report_text)
    db.add(report)
    await db.flush()
    await db.commit()

    return {"id": str(report.id), "week_start": report.week_start, "content": report.content, "created_at": report.created_at.isoformat()}


@router.get("/weekly/list", response_model=WeeklyReportListResponse)
async def list_weekly_reports(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeeklyReport).where(WeeklyReport.user_id == current_user.id)
        .order_by(WeeklyReport.week_start.desc()).limit(20)
    )
    reports = result.scalars().all()
    return {"reports": [
        {"id": str(r.id), "week_start": r.week_start, "content": r.content, "created_at": r.created_at.isoformat()}
        for r in reports
    ]}


@router.get("/check-monday")
async def check_monday_report(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if today is Monday. If yes, auto-generate last week's report and return it."""
    today = date.today()
    if today.weekday() != 0:  # Not Monday
        return {"is_monday": False, "report": None}

    # Check if user has API key configured
    if not current_user.ai_api_key:
        return {"is_monday": True, "report": None, "has_api_key": False}

    last_monday = today - timedelta(days=7)

    # Check if report already exists
    result = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.user_id == current_user.id, WeeklyReport.week_start == last_monday
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"is_monday": True, "report": {"id": str(existing.id), "week_start": str(existing.week_start), "content": existing.content}, "has_api_key": True}

    # Auto-generate daily summaries for last week
    summaries = []
    for i in range(7):
        d = last_monday + timedelta(days=i)
        summary = await _generate_daily_summary(current_user.id, d, db)
        summaries.append({
            "date": str(summary.date), "calories_in": summary.calories_in,
            "protein": summary.protein_grams, "carbs": summary.carbs_grams, "fat": summary.fat_grams,
            "water_ml": summary.water_ml, "workouts": summary.workout_count,
            "volume": summary.workout_volume, "calories_burned": summary.workout_calories,
            "minutes": summary.workout_minutes, "sleep_min": summary.sleep_minutes,
            "sleep_quality": summary.sleep_quality, "weight": summary.weight_kg,
            "health_records": summary.health_records_count, "health_abnormal": summary.health_abnormal_count,
        })

    user_data = json.dumps({"summaries": summaries}, ensure_ascii=False)

    try:
        content = await ai_service._call_llm_for_user(
            WEEKLY_REPORT_PROMPT, user_data, user=current_user, temperature=0.7, max_tokens=3000
        )
        parsed = json.loads(content.strip()) if content.strip().startswith("{") else {"overview": content}
        report_text = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        return {"is_monday": True, "report": None, "has_api_key": True, "error": "AI 生成失败"}

    report = WeeklyReport(user_id=current_user.id, week_start=last_monday, content=report_text)
    db.add(report)
    await db.flush()
    await db.commit()

    return {"is_monday": True, "report": {"id": str(report.id), "week_start": str(report.week_start), "content": report.content}, "has_api_key": True}
