import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.knowledge import KnowledgeCategoryEnum, KnowledgeEntry
from app.models.user import User

router = APIRouter()


# --- Pydantic Schemas ---

class KnowledgeEntryResponse(BaseModel):
    id: uuid.UUID
    category: KnowledgeCategoryEnum
    title: str
    content: str
    tags: Optional[list[str] | dict] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeEntryBriefResponse(BaseModel):
    id: uuid.UUID
    category: KnowledgeCategoryEnum
    title: str
    tags: Optional[list[str] | dict] = None
    source: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeEntryBriefResponse]
    total: int
    page: int
    page_size: int


# --- Endpoints ---

@router.get("", response_model=KnowledgeListResponse)
async def search_knowledge(
    q: Optional[str] = Query(default=None, description="Search query for title and content"),
    category: Optional[KnowledgeCategoryEnum] = Query(default=None, description="Filter by category"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search the knowledge base."""
    base_query = select(KnowledgeEntry)

    if q:
        base_query = base_query.where(
            (KnowledgeEntry.title.ilike(f"%{q}%")) | (KnowledgeEntry.content.ilike(f"%{q}%"))
        )
    if category:
        base_query = base_query.where(KnowledgeEntry.category == category)

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(KnowledgeEntry.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return KnowledgeListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a detailed knowledge base entry."""
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry
