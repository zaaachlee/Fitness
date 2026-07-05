from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import auth, users, foods, meals, exercises, workouts, health, dashboard, ai, knowledge, tracking, report

app = FastAPI(
    title="AI Fitness Dashboard API",
    description="Personal fitness management platform with AI-powered insights",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(foods.router, prefix="/api/v1/foods", tags=["Foods"])
app.include_router(meals.router, prefix="/api/v1/meals", tags=["Meals"])
app.include_router(exercises.router, prefix="/api/v1/exercises", tags=["Exercises"])
app.include_router(workouts.router, prefix="/api/v1/workouts", tags=["Workouts"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge"])
app.include_router(tracking.router, prefix="/api/v1/tracking", tags=["Tracking"])
app.include_router(report.router, prefix="/api/v1/report", tags=["Report"])


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
