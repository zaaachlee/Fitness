import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.exercise import Exercise, ExerciseTypeEnum
from app.models.user import User
from app.models.workout import WorkoutLog, WorkoutSet, WorkoutTemplate

router = APIRouter()


# --- Pydantic Schemas ---

class WorkoutSetResponse(BaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    set_number: int
    weight_kg: float
    reps: int
    rpe: Optional[float] = None
    is_warmup: bool = False
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class WorkoutSetCreateRequest(BaseModel):
    exercise_id: uuid.UUID
    set_number: int
    weight_kg: float
    reps: int
    rpe: Optional[float] = None
    is_warmup: bool = False
    notes: Optional[str] = None


class WorkoutLogCreateRequest(BaseModel):
    date: date
    template_id: Optional[uuid.UUID] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    body_weight_kg: Optional[float] = None
    sets: list[WorkoutSetCreateRequest] = []


class WorkoutLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    template_id: Optional[uuid.UUID] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    body_weight_kg: Optional[float] = None
    calories_burned: Optional[float] = None
    calories_source: Optional[str] = None
    created_at: datetime
    sets: list[WorkoutSetResponse] = []

    class Config:
        from_attributes = True


class WorkoutLogListResponse(BaseModel):
    workouts: list[WorkoutLogResponse]


class WorkoutTemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    exercises: list[dict] = []


class WorkoutTemplateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    exercises: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkoutTemplateListResponse(BaseModel):
    templates: list[WorkoutTemplateResponse]


class ExerciseStatsResponse(BaseModel):
    exercise_id: uuid.UUID
    exercise_name: str
    personal_record: Optional[float] = None  # max weight in kg
    total_volume_kg: float = 0.0  # sum(weight * reps)
    estimated_1rm: Optional[float] = None  # Epley formula
    total_sets: int = 0
    total_workouts: int = 0
    recent_weights: list[dict] = []  # [{date, weight_kg, reps}] last 10 sets


class WorkoutUpdateRequest(BaseModel):
    date: Optional[date] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    body_weight_kg: Optional[float] = None


class WorkoutTemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    exercises: Optional[list[dict]] = None


class ExerciseBriefResponse(BaseModel):
    id: uuid.UUID
    name: str
    primary_muscle: str
    equipment: Optional[str] = None

    class Config:
        from_attributes = True


# --- Helpers ---

def _calc_1rm(weight_kg: float, reps: int) -> float:
    """Estimate 1RM using the Epley formula."""
    if reps == 1:
        return round(weight_kg, 2)
    if reps > 0:
        return round(weight_kg * (1 + reps / 30.0), 2)
    return 0.0


# --- Endpoints ---

@router.get("", response_model=WorkoutLogListResponse)
async def list_workouts(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List workout history within a date range."""
    query = (
        select(WorkoutLog)
        .where(WorkoutLog.user_id == current_user.id)
        .options(selectinload(WorkoutLog.sets))
        .order_by(WorkoutLog.date.desc(), WorkoutLog.created_at.desc())
    )
    if date_from:
        query = query.where(WorkoutLog.date >= date_from)
    if date_to:
        query = query.where(WorkoutLog.date <= date_to)

    result = await db.execute(query)
    workouts = result.scalars().all()
    return WorkoutLogListResponse(workouts=workouts)


@router.get("/today", response_model=WorkoutLogListResponse)
async def get_today_workouts(
    target_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get workouts for a specific date (default today)."""
    today = target_date or date.today()
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == current_user.id, WorkoutLog.date == today)
        .options(selectinload(WorkoutLog.sets))
        .order_by(WorkoutLog.created_at.desc())
    )
    workouts = result.scalars().all()
    return WorkoutLogListResponse(workouts=workouts)


@router.post("/", response_model=WorkoutLogResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(
    body: WorkoutLogCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a workout log with sets."""
    workout = WorkoutLog(
        user_id=current_user.id,
        date=body.date,
        template_id=body.template_id,
        duration_minutes=body.duration_minutes,
        notes=body.notes,
        body_weight_kg=body.body_weight_kg,
    )
    db.add(workout)
    await db.flush()

    for set_req in body.sets:
        result = await db.execute(select(Exercise).where(Exercise.id == set_req.exercise_id))
        exercise = result.scalar_one_or_none()
        if exercise is None:
            raise HTTPException(status_code=404, detail=f"Exercise {set_req.exercise_id} not found")

        workout_set = WorkoutSet(
            workout_log_id=workout.id,
            exercise_id=set_req.exercise_id,
            set_number=set_req.set_number,
            weight_kg=set_req.weight_kg,
            reps=set_req.reps,
            rpe=set_req.rpe,
            is_warmup=set_req.is_warmup,
            notes=set_req.notes,
        )
        db.add(workout_set)

    # Auto-calculate calories from training volume (from request body)
    total_volume = sum(s.weight_kg * s.reps for s in body.sets)
    workout.calories_burned = round(total_volume * 0.08, 1)
    workout.calories_source = "estimated"

    await db.flush()
    await db.refresh(workout)

    # Reload with relationships
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.id == workout.id)
        .options(selectinload(WorkoutLog.sets))
    )
    return result.scalar_one()


@router.get("/exercises", response_model=list[ExerciseBriefResponse])
async def list_exercises(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List available exercises (delegates to exercises module in future)."""
    result = await db.execute(
        select(Exercise).where(Exercise.is_active == True).order_by(Exercise.name)
    )
    exercises = result.scalars().all()
    return exercises


@router.get("/exercises/{exercise_id}/stats", response_model=ExerciseStatsResponse)
async def get_exercise_stats(
    exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get exercise statistics: PR, volume, 1RM, and trend."""
    # Get the exercise info
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Get all sets for this exercise by this user
    result = await db.execute(
        select(WorkoutSet)
        .join(WorkoutLog)
        .where(
            WorkoutLog.user_id == current_user.id,
            WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.is_warmup == False,
        )
        .order_by(WorkoutLog.date.desc(), WorkoutSet.set_number.asc())
    )
    all_sets = result.scalars().all()

    if not all_sets:
        return ExerciseStatsResponse(
            exercise_id=exercise_id,
            exercise_name=exercise.name,
        )

    # Calculate PR (max weight)
    max_weight = max(s.weight_kg for s in all_sets)

    # Total volume
    total_volume = sum(s.weight_kg * s.reps for s in all_sets)

    # Estimated 1RM (best set)
    best_1rm = 0.0
    for s in all_sets:
        est = _calc_1rm(s.weight_kg, s.reps)
        if est > best_1rm:
            best_1rm = est

    # Count unique workouts
    workout_ids = set(s.workout_log_id for s in all_sets)

    # Recent weights (last 10 sets)
    recent = []
    # We need to get the date from the workout log for each set
    workout_date_map = {}
    unique_workout_ids = set(s.workout_log_id for s in all_sets[:20])
    if unique_workout_ids:
        result = await db.execute(
            select(WorkoutLog).where(WorkoutLog.id.in_(unique_workout_ids))
        )
        for wl in result.scalars().all():
            workout_date_map[wl.id] = wl.date

    for s in all_sets[:10]:
        recent.append({
            "date": str(workout_date_map.get(s.workout_log_id, "")),
            "weight_kg": s.weight_kg,
            "reps": s.reps,
        })

    return ExerciseStatsResponse(
        exercise_id=exercise_id,
        exercise_name=exercise.name,
        personal_record=max_weight,
        total_volume_kg=round(total_volume, 2),
        estimated_1rm=round(best_1rm, 2),
        total_sets=len(all_sets),
        total_workouts=len(workout_ids),
        recent_weights=recent,
    )


@router.post("/exercises", response_model=ExerciseBriefResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_exercise(
    name: str = Query(...),
    primary_muscle: str = Query(...),
    equipment: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom exercise (simplified version for quick add from workouts)."""
    exercise = Exercise(
        name=name,
        primary_muscle=primary_muscle,
        equipment=equipment,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(exercise)
    await db.flush()
    await db.refresh(exercise)
    return exercise


@router.get("/templates", response_model=WorkoutTemplateListResponse)
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List workout templates for the current user."""
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == current_user.id)
        .order_by(WorkoutTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return WorkoutTemplateListResponse(templates=templates)


@router.post("/templates", response_model=WorkoutTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: WorkoutTemplateCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a workout template."""
    template = WorkoutTemplate(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        exercises=body.exercises,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


# --- Single Workout CRUD ---

@router.get("/{workout_id}", response_model=WorkoutLogResponse)
async def get_workout(
    workout_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single workout with its sets."""
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.id == workout_id)
        .options(selectinload(WorkoutLog.sets))
    )
    workout = result.scalar_one_or_none()
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@router.put("/{workout_id}", response_model=WorkoutLogResponse)
async def update_workout(
    workout_id: uuid.UUID,
    body: WorkoutUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a workout's metadata (date, duration, notes, body_weight)."""
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.id == workout_id)
        .options(selectinload(WorkoutLog.sets))
    )
    workout = result.scalar_one_or_none()
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(workout, key, value)

    await db.commit()
    await db.refresh(workout)
    return workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a workout and all its sets (cascade)."""
    result = await db.execute(
        select(WorkoutLog).where(WorkoutLog.id == workout_id)
    )
    workout = result.scalar_one_or_none()
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")

    await db.delete(workout)
    await db.commit()
    return None


# --- Template CRUD ---

@router.put("/templates/{template_id}", response_model=WorkoutTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: WorkoutTemplateUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a workout template."""
    result = await db.execute(
        select(WorkoutTemplate).where(WorkoutTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None or template.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a workout template."""
    result = await db.execute(
        select(WorkoutTemplate).where(WorkoutTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None or template.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return None
