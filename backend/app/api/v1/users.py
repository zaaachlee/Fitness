import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User, UserProfile, UserWeightLog
from app.schemas.user import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserResponse,
    UserUpdateRequest,
    WeightLogRequest,
    WeightLogResponse,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get the current authenticated user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current authenticated user's basic profile."""
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user


class UserProfileFullResponse(BaseModel):
    user: UserResponse
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True


@router.get("/me/profile", response_model=UserProfileFullResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get the current user's fitness profile."""
    return UserProfileFullResponse(
        user=UserResponse.model_validate(current_user),
        profile=UserProfileResponse.model_validate(current_user.profile) if current_user.profile else None,
    )


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_user_profile(
    body: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's fitness profile."""
    profile = current_user.profile
    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.flush()
    await db.refresh(profile)
    return profile


@router.get("/me/weight-history", response_model=list[WeightLogResponse])
async def get_weight_history(
    limit: int = Query(default=90, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's weight log history."""
    result = await db.execute(
        select(UserWeightLog)
        .where(UserWeightLog.user_id == current_user.id)
        .order_by(UserWeightLog.date.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/me/weight", response_model=WeightLogResponse, status_code=status.HTTP_201_CREATED)
async def log_weight(
    body: WeightLogRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a new weight entry for the current user."""
    weight_log = UserWeightLog(
        user_id=current_user.id,
        date=body.date,
        weight_kg=body.weight_kg,
        body_fat_pct=body.body_fat_pct,
        notes=body.notes,
    )
    db.add(weight_log)
    await db.flush()
    await db.refresh(weight_log)
    await db.commit()
    return weight_log


# --- AI Settings ---

class AISettingsResponse(BaseModel):
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = None


class AISettingsUpdateRequest(BaseModel):
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = None


@router.get("/me/ai-settings", response_model=AISettingsResponse)
async def get_ai_settings(current_user: User = Depends(get_current_active_user)):
    return AISettingsResponse(
        ai_provider=current_user.ai_provider,
        ai_api_key=current_user.ai_api_key,
        ai_base_url=current_user.ai_base_url,
        ai_model=current_user.ai_model,
    )


@router.put("/me/ai-settings", response_model=AISettingsResponse)
async def update_ai_settings(
    body: AISettingsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if body.ai_provider is not None:
        current_user.ai_provider = body.ai_provider
    if body.ai_api_key is not None:
        current_user.ai_api_key = body.ai_api_key
    if body.ai_base_url is not None:
        current_user.ai_base_url = body.ai_base_url
    if body.ai_model is not None:
        current_user.ai_model = body.ai_model
    await db.flush()
    await db.commit()
    return AISettingsResponse(
        ai_provider=current_user.ai_provider,
        ai_api_key=current_user.ai_api_key,
        ai_base_url=current_user.ai_base_url,
        ai_model=current_user.ai_model,
    )


# --- Health Settings ---

class HealthSettingsResponse(BaseModel):
    settings: dict = {}


class HealthSettingsUpdateRequest(BaseModel):
    settings: dict


@router.get("/me/health-settings", response_model=HealthSettingsResponse)
async def get_health_settings(current_user: User = Depends(get_current_active_user)):
    return HealthSettingsResponse(settings=current_user.health_settings or {})


@router.put("/me/health-settings", response_model=HealthSettingsResponse)
async def update_health_settings(
    body: HealthSettingsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.health_settings = body.settings
    await db.flush()
    await db.commit()
    return HealthSettingsResponse(settings=current_user.health_settings)
