"""
Seed data loader — populates the database with initial data.
Run with: python -m app.seed.run
"""
import asyncio
import json
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session, engine, Base
from app.models.food import FoodItem
from app.models.exercise import Exercise
from app.models.health import HealthMetric
from app.models.knowledge import KnowledgeEntry

SEED_DIR = Path(__file__).parent


def load_json(filename: str) -> list[dict]:
    path = SEED_DIR / filename
    if not path.exists():
        print(f"(!)  Seed file not found: {filename}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_foods(session: AsyncSession):
    data = load_json("foods.json")
    if not data:
        return
    existing = await session.execute(select(FoodItem.id).limit(1))
    if existing.first():
        print(f"  - Foods already seeded, skipping ({len(data)} items available)")
        return
    for item in data:
        food = FoodItem(
            id=uuid.uuid4(),
            name=item["name"],
            name_en=item.get("name_en"),
            aliases=item.get("aliases"),
            category=item["category"],
            calories_per_100g=item["calories_per_100g"],
            protein_per_100g=item.get("protein_per_100g", 0),
            carbs_per_100g=item.get("carbs_per_100g", 0),
            fat_per_100g=item.get("fat_per_100g", 0),
            fiber_per_100g=item.get("fiber_per_100g"),
            sugar_per_100g=item.get("sugar_per_100g"),
            sodium_per_100g=item.get("sodium_per_100g"),
            cholesterol_per_100g=item.get("cholesterol_per_100g"),
            saturated_fat_per_100g=item.get("saturated_fat_per_100g"),
            gi=item.get("gi"),
            gl=item.get("gl"),
            purine_per_100g=item.get("purine_per_100g"),
            vitamins=item.get("vitamins"),
            minerals=item.get("minerals"),
            brand=item.get("brand"),
            barcode=item.get("barcode"),
            is_verified=item.get("is_verified", True),
        )
        session.add(food)
    await session.flush()
    print(f"  - Seeded {len(data)} food items")


async def seed_exercises(session: AsyncSession):
    data = load_json("exercises.json")
    if not data:
        return
    existing = await session.execute(select(Exercise.id).limit(1))
    if existing.first():
        print(f"  - Exercises already seeded, skipping ({len(data)} items available)")
        return
    for item in data:
        exercise = Exercise(
            id=uuid.uuid4(),
            name=item["name"],
            name_en=item.get("name_en"),
            primary_muscle=item["primary_muscle"],
            secondary_muscles=item.get("secondary_muscles"),
            equipment=item.get("equipment"),
            exercise_type=item["exercise_type"],
            met_value=item.get("met_value"),
            description=item.get("description"),
            instructions=item.get("instructions"),
            video_url=item.get("video_url"),
        )
        session.add(exercise)
    await session.flush()
    print(f"  - Seeded {len(data)} exercises")


async def seed_health_metrics(session: AsyncSession):
    data = load_json("health_metrics.json")
    if not data:
        return
    existing = await session.execute(select(HealthMetric.id).limit(1))
    if existing.first():
        print(f"  - Health metrics already seeded, skipping ({len(data)} items available)")
        return
    for item in data:
        metric = HealthMetric(
            id=uuid.uuid4(),
            name=item["name"],
            name_en=item.get("name_en"),
            unit=item["unit"],
            normal_range_min=item.get("normal_range_min"),
            normal_range_max=item.get("normal_range_max"),
            category=item["category"],
            clinical_significance=item.get("clinical_significance"),
            abnormal_risk=item.get("abnormal_risk"),
            dietary_advice=item.get("dietary_advice"),
            exercise_advice=item.get("exercise_advice"),
            reference_source=item.get("reference_source"),
        )
        session.add(metric)
    await session.flush()
    print(f"  - Seeded {len(data)} health metrics")


async def seed_knowledge(session: AsyncSession):
    data = load_json("knowledge.json")
    if not data:
        return
    existing = await session.execute(select(KnowledgeEntry.id).limit(1))
    if existing.first():
        print(f"  - Knowledge entries already seeded, skipping ({len(data)} items available)")
        return
    for item in data:
        entry = KnowledgeEntry(
            id=uuid.uuid4(),
            category=item["category"],
            title=item["title"],
            content=item["content"],
            tags=item.get("tags"),
            source=item.get("source"),
        )
        session.add(entry)
    await session.flush()
    print(f"  - Seeded {len(data)} knowledge entries")


async def run():
    print("[SEED] Starting seed data loader...")

    # Create tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        try:
            await seed_foods(session)
            await seed_exercises(session)
            await seed_health_metrics(session)
            await seed_knowledge(session)
            await session.commit()
            print("(!) Seed data loaded successfully!")
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Error seeding data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run())
