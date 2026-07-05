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
from app.models.food import FoodItem
from app.models.meal import FoodLog, MealLog, MealType
from app.models.user import User

router = APIRouter()


# --- Pydantic Schemas ---

class FoodLogResponse(BaseModel):
    id: uuid.UUID
    meal_log_id: uuid.UUID
    food_item_id: uuid.UUID
    weight_grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class MealLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    meal_type: MealType
    created_at: datetime
    food_logs: list[FoodLogResponse] = []

    class Config:
        from_attributes = True


class MealLogListResponse(BaseModel):
    meals: list[MealLogResponse]


class FoodLogCreateRequest(BaseModel):
    food_item_id: uuid.UUID
    weight_grams: float
    notes: Optional[str] = None


class MealLogCreateRequest(BaseModel):
    date: date
    meal_type: MealType
    foods: list[FoodLogCreateRequest] = []


class FoodLogUpdateRequest(BaseModel):
    weight_grams: Optional[float] = None
    notes: Optional[str] = None


class MealNutritionSummary(BaseModel):
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: float = 0.0
    total_sugar: float = 0.0
    total_sodium: float = 0.0


class TodayMealResponse(BaseModel):
    date: date
    meals: list[MealLogResponse]
    summary: MealNutritionSummary


# --- Helper ---

def _calc_nutrition_for_food(food: FoodItem, weight_grams: float) -> dict:
    """Calculate nutrition values for a given weight of food."""
    factor = weight_grams / 100.0
    return {
        "calories": round(food.calories_per_100g * factor, 2),
        "protein": round(food.protein_per_100g * factor, 2),
        "carbs": round(food.carbs_per_100g * factor, 2),
        "fat": round(food.fat_per_100g * factor, 2),
        "fiber": round(food.fiber_per_100g * factor, 2) if food.fiber_per_100g else None,
        "sugar": round(food.sugar_per_100g * factor, 2) if food.sugar_per_100g else None,
        "sodium": round(food.sodium_per_100g * factor, 2) if food.sodium_per_100g else None,
    }


# --- Endpoints ---

@router.get("", response_model=MealLogListResponse)
async def list_meals(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List meals within a date range."""
    query = (
        select(MealLog)
        .where(MealLog.user_id == current_user.id)
        .options(selectinload(MealLog.food_logs))
        .order_by(MealLog.date.desc(), MealLog.created_at.desc())
    )
    if date_from:
        query = query.where(MealLog.date >= date_from)
    if date_to:
        query = query.where(MealLog.date <= date_to)

    result = await db.execute(query)
    meals = result.scalars().all()
    return MealLogListResponse(meals=meals)


@router.get("/today", response_model=TodayMealResponse)
async def get_today_meals(
    target_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get meal summary for a specific date (default today)."""
    today = target_date or date.today()
    result = await db.execute(
        select(MealLog)
        .where(MealLog.user_id == current_user.id, MealLog.date == today)
        .options(selectinload(MealLog.food_logs))
        .order_by(MealLog.created_at.desc())
    )
    meals = result.scalars().all()

    summary = MealNutritionSummary()
    for meal in meals:
        for fl in meal.food_logs:
            summary.total_calories += fl.calories or 0
            summary.total_protein += fl.protein or 0
            summary.total_carbs += fl.carbs or 0
            summary.total_fat += fl.fat or 0
            summary.total_fiber += fl.fiber or 0
            summary.total_sugar += fl.sugar or 0
            summary.total_sodium += fl.sodium or 0

    # Round to 2 decimal places
    for field in ("total_calories", "total_protein", "total_carbs", "total_fat", "total_fiber", "total_sugar", "total_sodium"):
        setattr(summary, field, round(getattr(summary, field), 2))

    return TodayMealResponse(date=today, meals=meals, summary=summary)


@router.post("/", response_model=MealLogResponse, status_code=status.HTTP_201_CREATED)
async def create_meal(
    body: MealLogCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a meal log with optional food entries."""
    meal = MealLog(
        user_id=current_user.id,
        date=body.date,
        meal_type=body.meal_type,
    )
    db.add(meal)
    await db.flush()

    for food_req in body.foods:
        # Look up the food item for nutrition data
        result = await db.execute(select(FoodItem).where(FoodItem.id == food_req.food_item_id))
        food_item = result.scalar_one_or_none()
        if food_item is None:
            raise HTTPException(status_code=404, detail=f"Food item {food_req.food_item_id} not found")

        nutrition = _calc_nutrition_for_food(food_item, food_req.weight_grams)
        food_log = FoodLog(
            meal_log_id=meal.id,
            food_item_id=food_req.food_item_id,
            weight_grams=food_req.weight_grams,
            notes=food_req.notes,
            **nutrition,
        )
        db.add(food_log)

    await db.flush()
    await db.refresh(meal)

    # Reload with relationships
    result = await db.execute(
        select(MealLog)
        .where(MealLog.id == meal.id)
        .options(selectinload(MealLog.food_logs))
    )
    return result.scalar_one()


@router.post("/{meal_id}/foods", response_model=FoodLogResponse, status_code=status.HTTP_201_CREATED)
async def add_food_to_meal(
    meal_id: uuid.UUID,
    body: FoodLogCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a food entry to an existing meal."""
    result = await db.execute(
        select(MealLog).where(MealLog.id == meal_id, MealLog.user_id == current_user.id)
    )
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")

    result = await db.execute(select(FoodItem).where(FoodItem.id == body.food_item_id))
    food_item = result.scalar_one_or_none()
    if food_item is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    nutrition = _calc_nutrition_for_food(food_item, body.weight_grams)
    food_log = FoodLog(
        meal_log_id=meal.id,
        food_item_id=body.food_item_id,
        weight_grams=body.weight_grams,
        notes=body.notes,
        **nutrition,
    )
    db.add(food_log)
    await db.flush()
    await db.refresh(food_log)
    return food_log


@router.put("/foods/{food_log_id}", response_model=FoodLogResponse)
async def update_food_entry(
    food_log_id: uuid.UUID,
    body: FoodLogUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a food log entry's weight (recalculates nutrition)."""
    result = await db.execute(
        select(FoodLog)
        .join(MealLog)
        .where(FoodLog.id == food_log_id, MealLog.user_id == current_user.id)
    )
    food_log = result.scalar_one_or_none()
    if food_log is None:
        raise HTTPException(status_code=404, detail="Food log entry not found")

    if body.weight_grams is not None:
        result = await db.execute(select(FoodItem).where(FoodItem.id == food_log.food_item_id))
        food_item = result.scalar_one_or_none()
        if food_item:
            nutrition = _calc_nutrition_for_food(food_item, body.weight_grams)
            for key, value in nutrition.items():
                setattr(food_log, key, value)
        food_log.weight_grams = body.weight_grams

    if body.notes is not None:
        food_log.notes = body.notes

    await db.flush()
    await db.refresh(food_log)
    return food_log


@router.delete("/foods/{food_log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food_entry(
    food_log_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a food entry from a meal."""
    result = await db.execute(
        select(FoodLog)
        .join(MealLog)
        .where(FoodLog.id == food_log_id, MealLog.user_id == current_user.id)
    )
    food_log = result.scalar_one_or_none()
    if food_log is None:
        raise HTTPException(status_code=404, detail="Food log entry not found")

    await db.delete(food_log)
    await db.flush()


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an entire meal and all its food entries."""
    result = await db.execute(
        select(MealLog).where(MealLog.id == meal_id, MealLog.user_id == current_user.id)
    )
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")

    await db.delete(meal)
    await db.flush()
