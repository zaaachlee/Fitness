from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database — supports PostgreSQL (asyncpg) or SQLite (aiosqlite) for local dev
    DATABASE_URL: str = "sqlite+aiosqlite:///./fitness.db"
    DATABASE_URL_SYNC: str = "sqlite:///./fitness.db"

    # JWT
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Provider — supports: claude, openai, deepseek, openai-compatible
    AI_PROVIDER: str = "claude"

    # Claude API
    ANTHROPIC_API_KEY: str = ""

    # OpenAI API (also used for DeepSeek and other OpenAI-compatible providers)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""  # Leave empty for default; set for DeepSeek etc.
    OPENAI_MODEL: str = "gpt-4o"  # Model name for OpenAI/DeepSeek

    # App
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
