"""
src/api/routes/items.py
───────────────────────
Question item bank management.

POST   /api/v1/items/           → Create item (faculty only)
GET    /api/v1/items/           → List items with filters
GET    /api/v1/items/{id}       → Get single item
PUT    /api/v1/items/{id}       → Update item (faculty only)
DELETE /api/v1/items/{id}       → Delete item (faculty only)
POST   /api/v1/items/bulk       → Bulk create from JSON (faculty only)
POST   /api/v1/items/calibrate  → Re-run IRT calibration on responses
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import CurrentUser, FacultyUser
from src.db.models import ExamItem, get_db_session

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    subject: str = Field(..., max_length=100)
    topic: str = Field(..., max_length=200)
    content: str = Field(..., min_length=10)
    item_type: Literal["mcq", "open"] = "mcq"
    options: list[str] | None = Field(
        default=None,
        description="List of 4 answer options for MCQ",
        min_length=2,
        max_length=6,
    )
    correct_option: int | None = Field(
        default=None,
        ge=0,
        description="0-based index of correct option for MCQ",
    )
    # IRT parameters — start with defaults, auto-calibrate later
    irt_a: float = Field(default=1.0, ge=0.1, le=3.0, description="Discrimination")
    irt_b: float = Field(default=0.0, ge=-4.0, le=4.0, description="Difficulty")
    irt_c: float = Field(default=0.25, ge=0.0, le=0.5, description="Guessing")


class ItemResponse(BaseModel):
    item_id: str
    subject: str
    topic: str
    content: str
    item_type: str
    options: list[str] | None
    correct_option: int | None
    irt_a: float
    irt_b: float
    irt_c: float
    irt_calibrated: bool

    @classmethod
    def from_orm(cls, item: ExamItem) -> "ItemResponse":
        opts = item.options.get("choices") if item.options else None
        return cls(
            item_id=str(item.id),
            subject=item.subject,
            topic=item.topic,
            content=item.content,
            item_type=item.item_type,
            options=opts,
            correct_option=item.correct_option,
            irt_a=item.irt_a,
            irt_b=item.irt_b,
            irt_c=item.irt_c,
            irt_calibrated=item.irt_calibrated,
        )


class ItemUpdate(BaseModel):
    content: str | None = None
    options: list[str] | None = None
    correct_option: int | None = None
    irt_a: float | None = Field(default=None, ge=0.1, le=3.0)
    irt_b: float | None = Field(default=None, ge=-4.0, le=4.0)
    irt_c: float | None = Field(default=None, ge=0.0, le=0.5)


# ── Routes ────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create exam item (faculty only)",
)
async def create_item(
    body: ItemCreate,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> ItemResponse:
    """Create a new question in the item bank."""
    # Validate MCQ has options and correct_option
    if body.item_type == "mcq":
        if not body.options or body.correct_option is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="MCQ items require 'options' list and 'correct_option' index.",
            )
        if body.correct_option >= len(body.options):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"correct_option index {body.correct_option} out of range for {len(body.options)} options.",
            )

    item = ExamItem(
        subject=body.subject,
        topic=body.topic,
        content=body.content,
        item_type=body.item_type,
        options={"choices": body.options} if body.options else None,
        correct_option=body.correct_option,
        irt_a=body.irt_a,
        irt_b=body.irt_b,
        irt_c=body.irt_c,
        created_by=current_user.id,
    )
    db.add(item)
    await db.flush()
    return ItemResponse.from_orm(item)


@router.get(
    "/",
    response_model=dict,
    summary="List all items with optional filters",
)
async def list_items(
    subject: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    item_type: str | None = Query(default=None),
    calibrated_only: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    query = select(ExamItem)
    if subject:
        query = query.where(ExamItem.subject.ilike(f"%{subject}%"))
    if topic:
        query = query.where(ExamItem.topic.ilike(f"%{topic}%"))
    if item_type:
        query = query.where(ExamItem.item_type == item_type)
    if calibrated_only:
        query = query.where(ExamItem.irt_calibrated == True)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(ExamItem.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    # Faculty/admin see correct_option; students don't
    is_faculty = current_user and current_user.role in ("faculty", "admin")

    return {
        "items": [
            {
                "item_id": str(i.id),
                "subject": i.subject,
                "topic": i.topic,
                "content": i.content,
                "item_type": i.item_type,
                "options": i.options.get("choices") if i.options else None,
                # Hide correct answer from students
                "correct_option": i.correct_option if is_faculty else None,
                "irt_b": i.irt_b,           # difficulty is fine to show
                "irt_calibrated": i.irt_calibrated,
            }
            for i in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get a single item",
)
async def get_item(
    item_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> ItemResponse:
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

    item = await db.get(ExamItem, iid)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse.from_orm(item)


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item (faculty only)",
)
async def update_item(
    item_id: str,
    body: ItemUpdate,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> ItemResponse:
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

    item = await db.get(ExamItem, iid)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if body.content is not None:
        item.content = body.content
    if body.options is not None:
        item.options = {"choices": body.options}
    if body.correct_option is not None:
        item.correct_option = body.correct_option
    if body.irt_a is not None:
        item.irt_a = body.irt_a
    if body.irt_b is not None:
        item.irt_b = body.irt_b
    if body.irt_c is not None:
        item.irt_c = body.irt_c
        item.irt_calibrated = True  # Manual override counts as calibrated

    return ItemResponse.from_orm(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item (faculty only)",
)
async def delete_item(
    item_id: str,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

    item = await db.get(ExamItem, iid)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)


@router.post(
    "/bulk",
    summary="Bulk create items from JSON list (faculty only)",
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_items(
    items: list[ItemCreate],
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Create multiple items at once.
    Useful for seeding from past paper JSON.
    Max 200 items per request.
    """
    if len(items) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 200 items per bulk request.",
        )

    created = []
    for body in items:
        item = ExamItem(
            subject=body.subject,
            topic=body.topic,
            content=body.content,
            item_type=body.item_type,
            options={"choices": body.options} if body.options else None,
            correct_option=body.correct_option,
            irt_a=body.irt_a,
            irt_b=body.irt_b,
            irt_c=body.irt_c,
            created_by=current_user.id,
        )
        db.add(item)
        created.append(item)

    await db.flush()

    return {
        "created": len(created),
        "item_ids": [str(i.id) for i in created],
    }