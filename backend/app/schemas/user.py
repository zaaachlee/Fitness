from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
import uuid


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    activity_level: str
    goal: str
    daily_calorie_target: Optional[int] = None
    daily_protein_target: Optional[int] = None
    daily_carbs_target: Optional[int] = None
    daily_fat_target: Optional[int] = None
    daily_water_target_ml: Optional[int] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None


class UserProfileUpdateRequest(BaseModel):
    activity_level: Optional[str] = None
    goal: Optional[str] = None
    daily_calorie_target: Optional[int] = None
    daily_protein_target: Optional[int] = None
    daily_carbs_target: Optional[int] = None
    daily_fat_target: Optional[int] = None
    daily_water_target_ml: Optional[int] = None


class WeightLogRequest(BaseModel):
    date: date
    weight_kg: float
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None


class WeightLogResponse(BaseModel):
    id: uuid.UUID
    date: date
    weight_kg: float
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
