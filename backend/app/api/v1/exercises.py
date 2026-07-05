import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.exercise import Exercise, ExerciseTypeEnum
from app.models.user import User

router = APIRouter()


# --- Pydantic Schemas ---

class ExerciseCreateRequest(BaseModel):
    name: str
    name_en: Optional[str] = None
    primary_muscle: str
    secondary_muscles: Optional[list[str]] = None
    equipment: Optional[str] = None
    exercise_type: ExerciseTypeEnum = ExerciseTypeEnum.COMPOUND
    met_value: Optional[float] = None
    description: Optional[str] = None
    instructions: Optional[list[str]] = None
    video_url: Optional[str] = None


class ExerciseResponse(BaseModel):
    id: uuid.UUID
    name: str
    name_en: Optional[str] = None
    primary_muscle: str
    secondary_muscles: Optional[list[str] | dict] = None
    equipment: Optional[str] = None
    exercise_type: ExerciseTypeEnum
    met_value: Optional[float] = None
    description: Optional[str] = None
    instructions: Optional[list[str] | dict] = None
    video_url: Optional[str] = None
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExerciseListResponse(BaseModel):
    items: list[ExerciseResponse]
    total: int
    page: int
    page_size: int


# --- Endpoints ---

@router.get("", response_model=ExerciseListResponse)
async def search_exercises(
    q: Optional[str] = Query(default=None, description="Search query for exercise name"),
    primary_muscle: Optional[str] = Query(default=None, description="Filter by primary muscle group"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search the exercise database."""
    base_query = select(Exercise).where(Exercise.is_active == True)

    if q:
        base_query = base_query.where(
            (Exercise.name.ilike(f"%{q}%")) | (Exercise.name_en.ilike(f"%{q}%"))
        )
    if primary_muscle:
        base_query = base_query.where(Exercise.primary_muscle == primary_muscle)

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(Exercise.name).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return ExerciseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(
    exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single exercise by ID."""
    result = await db.execute(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.is_active == True)
    )
    exercise = result.scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@router.post("/", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_exercise(
    body: ExerciseCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom exercise."""
    exercise = Exercise(
        created_by=current_user.id,
        is_active=True,
        **body.model_dump(exclude_unset=True),
    )
    db.add(exercise)
    await db.flush()
    await db.refresh(exercise)
    return exercise
