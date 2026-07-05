import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.food import FoodItem
from app.models.meal import FoodLog, MealLog
from app.models.user import User

router = APIRouter()


# --- Pydantic Schemas ---

class FoodItemCreateRequest(BaseModel):
    name: str
    name_en: Optional[str] = None
    aliases: Optional[list[str]] = None
    category: str
    calories_per_100g: float
    protein_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    fiber_per_100g: Optional[float] = None
    sugar_per_100g: Optional[float] = None
    sodium_per_100g: Optional[float] = None
    cholesterol_per_100g: Optional[float] = None
    saturated_fat_per_100g: Optional[float] = None
    trans_fat_per_100g: Optional[float] = None
    gi: Optional[float] = None
    gl: Optional[float] = None
    purine_per_100g: Optional[float] = None
    vitamins: Optional[dict] = None
    minerals: Optional[dict] = None
    brand: Optional[str] = None
    barcode: Optional[str] = None


class FoodItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    name_en: Optional[str] = None
    aliases: Optional[list[str] | dict] = None
    category: str
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: Optional[float] = None
    sugar_per_100g: Optional[float] = None
    sodium_per_100g: Optional[float] = None
    cholesterol_per_100g: Optional[float] = None
    saturated_fat_per_100g: Optional[float] = None
    trans_fat_per_100g: Optional[float] = None
    gi: Optional[float] = None
    gl: Optional[float] = None
    purine_per_100g: Optional[float] = None
    vitamins: Optional[dict] = None
    minerals: Optional[dict] = None
    brand: Optional[str] = None
    barcode: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FoodItemListResponse(BaseModel):
    items: list[FoodItemResponse]
    total: int
    page: int
    page_size: int


# --- Endpoints ---

@router.get("", response_model=FoodItemListResponse)
async def search_foods(
    q: Optional[str] = Query(default=None, description="Search query for food name"),
    category: Optional[str] = Query(default=None, description="Filter by food category"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search the food database with optional filters."""
    base_query = select(FoodItem).where(FoodItem.is_active == True)

    if q:
        base_query = base_query.where(FoodItem.name.ilike(f"%{q}%"))
    if category:
        base_query = base_query.where(FoodItem.category == category)

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(FoodItem.name).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return FoodItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{food_id}", response_model=FoodItemResponse)
async def get_food_detail(
    food_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific food item."""
    result = await db.execute(
        select(FoodItem).where(FoodItem.id == food_id, FoodItem.is_active == True)
    )
    food = result.scalar_one_or_none()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")
    return food


@router.get("/recent/list", response_model=FoodItemListResponse)
async def get_recent_foods(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, le=50),
):
    """Get foods recently logged by the current user."""
    # Subquery for distinct food_item_ids from user's recent food logs
    recent_subq = (
        select(FoodLog.food_item_id, func.max(FoodLog.id).label("max_id"))
        .join(MealLog, MealLog.id == FoodLog.meal_log_id)
        .where(MealLog.user_id == current_user.id)
        .group_by(FoodLog.food_item_id)
        .order_by(func.max(FoodLog.id).desc())
        .limit(limit)
        .subquery()
    )

    result = await db.execute(
        select(FoodItem)
        .join(recent_subq, FoodItem.id == recent_subq.c.food_item_id)
        .where(FoodItem.is_active == True)
        .order_by(recent_subq.c.max_id.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    return FoodItemListResponse(items=items, total=len(items), page=1, page_size=len(items))


@router.post("/", response_model=FoodItemResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_food(
    body: FoodItemCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom food item."""
    food = FoodItem(
        created_by=current_user.id,
        is_verified=False,
        **body.model_dump(exclude_unset=True),
    )
    db.add(food)
    await db.flush()
    await db.refresh(food)
    return food
