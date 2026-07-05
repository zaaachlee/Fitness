import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User, UserProfile
from app.models.meal import MealLog, FoodLog
from app.models.workout import WorkoutLog, WorkoutSet
from app.models.exercise import Exercise
from app.models.chat import AIChatMessage, ChatRoleEnum
from app.services import ai_service

router = APIRouter()


# --- Pydantic Schemas ---

class AIChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


class AIChatResponse(BaseModel):
    reply: str
    model: str = "claude"


class AnalyzedFoodItem(BaseModel):
    name: str
    estimated_weight_grams: float
    estimated_calories: float
    estimated_protein: float
    estimated_carbs: float
    estimated_fat: float
    confidence: float


class AnalyzeFoodTextRequest(BaseModel):
    text: str


class AnalyzeFoodTextResponse(BaseModel):
    foods: list[AnalyzedFoodItem] = []
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    notes: str = ""


class AnalyzeFoodImageResponse(BaseModel):
    foods: list[AnalyzedFoodItem] = []
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    notes: str = ""


class DailyAdviceResponse(BaseModel):
    date: date
    advice: str
    nutrition_tip: str = ""
    workout_tip: str = ""
    health_tip: str = ""


class WorkoutAdviceResponse(BaseModel):
    exercise_id: uuid.UUID
    exercise_name: str
    advice: str
    form_tips: list[str] = []
    progression_suggestion: str = ""


# --- Endpoints ---

CHAT_SYSTEM_PROMPT = """你是 AI Fitness Dashboard 的 AI 健身助手。你可以访问用户的饮食记录、训练数据和健康指标。

你的角色是：
1. 根据用户的历史数据回答健身、营养和健康相关问题
2. 提供个性化建议，而非泛泛而谈
3. 如果用户问的问题需要查看他们的数据，主动提及数据中的具体数字
4. 保持专业、鼓励、实用的语气
5. 所有回答用中文

用户数据摘要会随每次对话自动注入。"""


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """AI chat with real LLM and history persistence."""
    # Get recent chat history
    history_result = await db.execute(
        select(AIChatMessage)
        .where(AIChatMessage.user_id == current_user.id)
        .order_by(AIChatMessage.created_at.desc())
        .limit(20)
    )
    history = history_result.scalars().all()
    history = list(reversed(history))  # chronological order

    # Build messages for LLM
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h.role.value, "content": h.content})
    messages.append({"role": "user", "content": body.message})

    # Save user message
    user_msg = AIChatMessage(user_id=current_user.id, role=ChatRoleEnum.USER, content=body.message)
    db.add(user_msg)
    await db.flush()

    # Call LLM with user's personal config
    try:
        cfg = ai_service.get_user_ai_config(user=current_user)
        if cfg["provider"] == "claude":
            client = ai_service._get_claude(api_key=cfg["api_key"])
            response = client.messages.create(
                model=cfg["model"], max_tokens=2048, temperature=0.7,
                system=CHAT_SYSTEM_PROMPT,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            )
            reply = response.content[0].text
        else:
            client = ai_service._get_openai(api_key=cfg["api_key"], base_url=cfg["base_url"])
            response = await client.chat.completions.create(
                model=cfg["model"], temperature=0.7, max_tokens=2048,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            )
            reply = response.choices[0].message.content or ""
    except Exception as e:
        reply = f"抱歉，AI 服务暂时不可用。请稍后重试。（错误：{str(e)[:100]}）"

    # Save AI reply
    ai_msg = AIChatMessage(user_id=current_user.id, role=ChatRoleEnum.ASSISTANT, content=reply)
    db.add(ai_msg)
    await db.flush()
    await db.commit()

    return AIChatResponse(reply=reply, model=ai_service.get_provider())


@router.get("/chat/history", response_model=list[dict])
async def get_chat_history(
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for the current user."""
    result = await db.execute(
        select(AIChatMessage)
        .where(AIChatMessage.user_id == current_user.id)
        .order_by(AIChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return [
        {"id": str(m.id), "role": m.role.value, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in reversed(messages)
    ]


@router.post("/analyze-food-text", response_model=AnalyzeFoodTextResponse)
async def analyze_food_text(
    body: AnalyzeFoodTextRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Analyze food from natural language text using Claude AI."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="请输入食物描述")

    try:
        result = await ai_service.analyze_food_text(body.text, user=current_user)
        foods = [AnalyzedFoodItem(**f) for f in result.get("foods", [])]
        return AnalyzeFoodTextResponse(
            foods=foods,
            total_calories=result.get("total_calories", 0),
            total_protein=result.get("total_protein", 0),
            total_carbs=result.get("total_carbs", 0),
            total_fat=result.get("total_fat", 0),
            notes=result.get("notes", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")


@router.post("/analyze-food-image", response_model=AnalyzeFoodImageResponse)
async def analyze_food_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """Analyze food from image upload (reserved for future Vision API integration)."""
    contents = await file.read()
    _ = len(contents)  # File received successfully
    return AnalyzeFoodImageResponse(
        foods=[],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        notes=f"已收到图片（{file.filename}, {len(contents)} bytes）。图片识别功能即将上线，当前支持文字描述识别。",
    )


@router.get("/daily-advice", response_model=DailyAdviceResponse)
async def get_daily_advice(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated daily advice based on user's recent data."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Gather recent meal data
    meal_query = (
        select(
            func.coalesce(func.sum(FoodLog.calories), 0).label("total_calories"),
            func.coalesce(func.sum(FoodLog.protein), 0).label("total_protein"),
            func.coalesce(func.sum(FoodLog.carbs), 0).label("total_carbs"),
            func.coalesce(func.sum(FoodLog.fat), 0).label("total_fat"),
        )
        .select_from(MealLog)
        .join(FoodLog, FoodLog.meal_log_id == MealLog.id)
        .where(MealLog.user_id == current_user.id, MealLog.date >= week_ago)
    )
    meal_result = await db.execute(meal_query)
    meal_stats = meal_result.one()

    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    # Count workouts
    workout_count_result = await db.execute(
        select(func.count(WorkoutLog.id))
        .where(WorkoutLog.user_id == current_user.id, WorkoutLog.date >= week_ago)
    )
    workout_count = workout_count_result.scalar() or 0

    # Build context
    user_data = {
        "name": current_user.name,
        "goal": profile.goal.value if profile else "maintain",
        "today": str(today),
        "recent_7d": {
            "avg_daily_calories": round(meal_stats.total_calories / 7, 0) if meal_stats.total_calories else 0,
            "avg_daily_protein": round(meal_stats.total_protein / 7, 0) if meal_stats.total_protein else 0,
            "workout_count": workout_count,
        },
    }

    try:
        advice = await ai_service.generate_daily_advice(user_data, user=current_user)
        return DailyAdviceResponse(
            date=today,
            advice=advice.get("advice", ""),
            nutrition_tip=advice.get("nutrition_tip", ""),
            workout_tip=advice.get("workout_tip", ""),
            health_tip=advice.get("health_tip", ""),
        )
    except Exception:
        return DailyAdviceResponse(
            date=today,
            advice=f"你好 {current_user.name}！继续保持你的健身计划。",
            nutrition_tip="记录每一餐，AI 才能更好地帮助你。",
            workout_tip="坚持训练，渐进超负荷是关键。",
            health_tip="充足的睡眠是恢复的基础。",
        )


@router.get("/workout-advice/{exercise_id}", response_model=WorkoutAdviceResponse)
async def get_workout_advice(
    exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated workout advice based on exercise history."""
    # Get exercise info
    ex_result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = ex_result.scalar_one_or_none()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Get recent sets for this exercise
    thirty_days_ago = date.today() - timedelta(days=30)
    sets_result = await db.execute(
        select(WorkoutSet)
        .join(WorkoutLog, WorkoutLog.id == WorkoutSet.workout_log_id)
        .where(
            WorkoutLog.user_id == current_user.id,
            WorkoutSet.exercise_id == exercise_id,
            WorkoutLog.date >= thirty_days_ago,
        )
        .order_by(WorkoutLog.date.desc())
        .limit(30)
    )
    recent_sets = sets_result.scalars().all()

    # Build exercise data context
    exercise_data = {
        "name": exercise.name,
        "name_en": exercise.name_en,
        "primary_muscle": exercise.primary_muscle,
        "exercise_type": exercise.exercise_type.value,
        "recent_sets": [
            {"weight_kg": s.weight_kg, "reps": s.reps, "rpe": s.rpe}
            for s in recent_sets[:15]
        ],
        "total_sessions": len(set(s.workout_log_id for s in recent_sets)),
    }

    try:
        advice = await ai_service.generate_workout_advice(exercise_data, user=current_user)
        return WorkoutAdviceResponse(
            exercise_id=exercise_id,
            exercise_name=exercise.name,
            advice=advice.get("advice", ""),
            form_tips=advice.get("form_tips", []),
            progression_suggestion=advice.get("progression_suggestion", ""),
        )
    except Exception:
        return WorkoutAdviceResponse(
            exercise_id=exercise_id,
            exercise_name=exercise.name,
            advice="暂时无法生成训练建议，请检查网络后重试。",
            form_tips=["保持动作全程控制", "注重离心阶段的慢速下降", "保持呼吸节奏"],
            progression_suggestion="继续执行渐进超负荷计划。",
        )


# --- Workout Calorie Analysis ---

class WorkoutCalorieRequest(BaseModel):
    exercises: list[dict]  # [{ name, sets: [{ weight_kg, reps }] }]
    duration_minutes: int = 0
    body_weight_kg: float | None = None
    age: int | None = None
    gender: str | None = None


class WorkoutCalorieResponse(BaseModel):
    total_calories: float = 0
    breakdown: list[dict] = []
    notes: str = ""


WORKOUT_CALORIE_PROMPT = """你是运动生理学专家。根据用户的训练数据和身体信息，精准计算训练热量消耗。

计算方法：
1. 对于每个动作，计算总训练容量（重量kg × 次数 × 组数）
2. 根据动作类型估算MET值（复合动作6-8，孤立动作3-5，腿部复合动作可达8-10）
3. 热量 = MET × 体重kg × 时间(小时)
4. 结合训练容量和时长做加权调整

返回 JSON：
{
  "total_calories": 总消耗热量(千卡),
  "breakdown": [
    {"exercise_name": "杠铃卧推", "calories": 120, "met_used": 6.0}
  ],
  "notes": "简短分析（1句中文）"
}

用中文输出notes。精确计算，不要高估。"""


@router.post("/analyze-workout-calories", response_model=WorkoutCalorieResponse)
async def analyze_workout_calories(
    body: WorkoutCalorieRequest,
    current_user: User = Depends(get_current_active_user),
):
    """AI-powered workout calorie burn estimation using personal API key."""
    user_data = {
        "exercises": body.exercises,
        "duration_minutes": body.duration_minutes,
        "body_weight_kg": body.body_weight_kg,
        "age": body.age,
        "gender": body.gender,
    }
    try:
        content = await ai_service._call_llm_for_user(
            WORKOUT_CALORIE_PROMPT,
            json.dumps(user_data, ensure_ascii=False),
            user=current_user,
            temperature=0.1,
            max_tokens=1024,
        )
        result = ai_service._extract_json(content)
        return WorkoutCalorieResponse(
            total_calories=result.get("total_calories", 0),
            breakdown=result.get("breakdown", []),
            notes=result.get("notes", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")
