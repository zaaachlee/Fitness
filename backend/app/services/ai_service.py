"""
AI Service — Multi-provider support for Claude, OpenAI, DeepSeek, and compatible APIs.
"""
import json
import logging
from typing import Optional

from anthropic import Anthropic
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_claude: Optional[Anthropic] = None
_openai: Optional[AsyncOpenAI] = None


def get_provider() -> str:
    return settings.AI_PROVIDER


def get_user_ai_config(user=None) -> dict:
    """Get AI config, preferring user settings over global .env."""
    if user and user.ai_provider and user.ai_api_key:
        return {
            "provider": user.ai_provider,
            "api_key": user.ai_api_key,
            "base_url": user.ai_base_url or None,
            "model": user.ai_model or "gpt-4o",
        }
    return {
        "provider": settings.AI_PROVIDER,
        "api_key": settings.ANTHROPIC_API_KEY if settings.AI_PROVIDER == "claude" else settings.OPENAI_API_KEY,
        "base_url": settings.OPENAI_BASE_URL or None,
        "model": settings.OPENAI_MODEL,
    }


def _get_claude(api_key: str = None) -> Anthropic:
    key = api_key or settings.ANTHROPIC_API_KEY
    return Anthropic(api_key=key)


def _get_openai(api_key: str = None, base_url: str = None) -> AsyncOpenAI:
    key = api_key or settings.OPENAI_API_KEY
    url = base_url or settings.OPENAI_BASE_URL or None
    return AsyncOpenAI(api_key=key, base_url=url)


async def _call_llm_for_user(
    system_prompt: str, user_message: str, user=None,
    temperature: float = 0.1, max_tokens: int = 2048
) -> str:
    """Call LLM with user's personal API config if available."""
    cfg = get_user_ai_config(user)
    provider = cfg["provider"]

    if provider == "claude":
        client = _get_claude(api_key=cfg["api_key"])
        response = client.messages.create(
            model="claude-sonnet-5", max_tokens=max_tokens, temperature=temperature,
            system=system_prompt, messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    else:
        client = _get_openai(api_key=cfg["api_key"], base_url=cfg["base_url"])
        response = await client.chat.completions.create(
            model=cfg["model"], temperature=temperature, max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""


# ========================================
# System Prompts
# ========================================

FOOD_ANALYSIS_PROMPT = """你是一个专业的运动营养学 AI 助手，擅长分析食物营养成分。

用户会用自然语言描述他们吃了什么。你需要：
1. 识别出每种食物
2. 估算每种食物的重量（克）
3. 估算每种食物的热量（千卡）、蛋白质（克）、碳水（克）、脂肪（克）
4. 给出总汇总

严格按照以下 JSON 格式返回，不要包含额外文字：

{
  "foods": [
    {
      "name": "食物名称",
      "estimated_weight_grams": 重量,
      "estimated_calories": 热量,
      "estimated_protein": 蛋白质,
      "estimated_carbs": 碳水,
      "estimated_fat": 脂肪,
      "confidence": 0.0-1.0
    }
  ],
  "total_calories": 总热量,
  "total_protein": 总蛋白质,
  "total_carbs": 总碳水,
  "total_fat": 总脂肪,
  "notes": "简短分析说明（1-2句中文）"
}

规则：使用中国常见食物的标准营养数据；重量估算要合理；confidence 清晰=0.9+，中等=0.7-0.9，模糊=0.5-0.7"""

DAILY_ADVICE_PROMPT = """你是专业的 AI 健身教练和营养师。根据用户数据提供个性化建议。

分析数据后返回 JSON：
{
  "advice": "今日主要建议",
  "nutrition_tip": "营养提示",
  "workout_tip": "训练提示",
  "health_tip": "健康提示"
}

建议必须基于数据，不能泛泛而谈。用中文。"""

WORKOUT_ADVICE_PROMPT = """你是专业的健身教练 AI。根据动作历史分析并给出建议。

返回 JSON：
{
  "advice": "综合分析建议（2-3句）",
  "form_tips": ["技巧1", "技巧2", "技巧3"],
  "progression_suggestion": "进阶建议"
}

用中文。"""


# ========================================
# Core LLM Call
# ========================================

def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response (handles markdown wrapping)."""
    content = text.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    return json.loads(content.strip())


async def _call_claude(system_prompt: str, user_message: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    client = _get_claude()
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


async def _call_openai(system_prompt: str, user_message: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    client = _get_openai()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


async def _call_llm(system_prompt: str, user_message: str, temperature: float = 0.1, max_tokens: int = 2048, user=None) -> str:
    """Route to the configured AI provider, preferring user config."""
    return await _call_llm_for_user(system_prompt, user_message, user, temperature, max_tokens)


# ========================================
# Public API
# ========================================

async def analyze_food_text(text: str, user=None) -> dict:
    try:
        content = await _call_llm(FOOD_ANALYSIS_PROMPT, text, temperature=0.1, user=user)
        return _extract_json(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return {"foods": [], "total_calories": 0, "total_protein": 0, "total_carbs": 0, "total_fat": 0,
                "notes": f"AI 解析失败，请手动输入。原始输入：{text[:50]}..."}
    except Exception as e:
        logger.error(f"LLM error: {e}")
        raise


async def generate_daily_advice(user_data: dict, user=None) -> dict:
    try:
        content = await _call_llm(DAILY_ADVICE_PROMPT, json.dumps(user_data, ensure_ascii=False, default=str), temperature=0.7, max_tokens=1024, user=user)
        return _extract_json(content)
    except Exception as e:
        logger.error(f"Daily advice error: {e}")
        return {"advice": "暂时无法生成 AI 建议。", "nutrition_tip": "保持均衡饮食。", "workout_tip": "坚持规律训练。", "health_tip": "充足睡眠和水分是恢复的基础。"}


async def generate_workout_advice(exercise_data: dict, user=None) -> dict:
    try:
        content = await _call_llm(WORKOUT_ADVICE_PROMPT, json.dumps(exercise_data, ensure_ascii=False, default=str), temperature=0.7, max_tokens=1024, user=user)
        return _extract_json(content)
    except Exception as e:
        logger.error(f"Workout advice error: {e}")
        return {"advice": "暂时无法生成训练建议。", "form_tips": ["保持动作全程控制", "注重离心阶段", "保持呼吸节奏"], "progression_suggestion": "继续渐进超负荷。"}
