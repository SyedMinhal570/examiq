"""
src/api/routes/analytics.py
────────────────────────────
Analytics endpoints for faculty dashboard.

GET /api/v1/analytics/overview          → Platform KPIs
GET /api/v1/analytics/exam/{id}         → Per-exam stats
GET /api/v1/analytics/exam/{id}/flags   → Flagged students
GET /api/v1/analytics/item/{id}         → Item analysis (IRT)
POST /api/v1/analytics/exams            → Create new exam (faculty)
GET  /api/v1/analytics/exams            → List all exams
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import CurrentUser, FacultyUser
from src.db.models import Exam, ExamItem, ExamSession, ItemResponse as ItemResponseModel, User, get_db_session

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────

class CreateExamRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=300)
    subject: str = Field(..., max_length=100)
    max_items: int = Field(default=30, ge=5, le=100)
    time_limit_minutes: int = Field(default=60, ge=10, le=360)
    is_adaptive: bool = True


# ── Routes ────────────────────────────────────────────────────────

@router.post("/exams", status_code=201, summary="Create a new exam (faculty)")
async def create_exam(
    body: CreateExamRequest,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    exam = Exam(
        title=body.title,
        subject=body.subject,
        max_items=body.max_items,
        time_limit_minutes=body.time_limit_minutes,
        is_adaptive=body.is_adaptive,
        created_by=current_user.id,
        status="draft",
    )
    db.add(exam)
    await db.flush()
    return {
        "exam_id": str(exam.id),
        "title": exam.title,
        "subject": exam.subject,
        "status": exam.status,
        "message": "Exam created. Publish it with PUT /analytics/exams/{id}/publish",
    }


@router.put("/exams/{exam_id}/publish", summary="Publish exam (make active)")
async def publish_exam(
    exam_id: str,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        eid = uuid.UUID(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    exam = await db.get(Exam, eid)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if str(exam.created_by) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the creator can publish this exam")

    # Check there are items for this subject
    count_result = await db.execute(
        select(func.count(ExamItem.id)).where(ExamItem.subject == exam.subject)
    )
    item_count = count_result.scalar() or 0
    if item_count < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 10 items for subject '{exam.subject}'. Currently have {item_count}.",
        )

    exam.status = "active"
    return {"exam_id": exam_id, "status": "active", "item_count": item_count}


@router.get("/exams", summary="List all exams")
async def list_exams(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    query = select(Exam).order_by(Exam.created_at.desc()).limit(100)
    result = await db.execute(query)
    exams = result.scalars().all()

    return {
        "exams": [
            {
                "exam_id": str(e.id),
                "title": e.title,
                "subject": e.subject,
                "status": e.status,
                "is_adaptive": e.is_adaptive,
                "max_items": e.max_items,
                "time_limit_minutes": e.time_limit_minutes,
                "created_at": e.created_at.isoformat(),
            }
            for e in exams
        ]
    }


@router.get("/overview", summary="Platform overview KPIs")
async def get_overview(
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """High-level dashboard KPIs."""
    total_students = await db.execute(
        select(func.count(User.id)).where(User.role == "student")
    )
    total_items = await db.execute(select(func.count(ExamItem.id)))
    total_sessions = await db.execute(select(func.count(ExamSession.id)))
    completed_sessions = await db.execute(
        select(func.count(ExamSession.id)).where(ExamSession.status == "completed")
    )
    flagged_sessions = await db.execute(
        select(func.count(ExamSession.id)).where(ExamSession.collusion_flag == True)
    )
    avg_theta = await db.execute(
        select(func.avg(ExamSession.theta_final)).where(
            ExamSession.theta_final.isnot(None)
        )
    )

    return {
        "total_students": total_students.scalar() or 0,
        "total_items": total_items.scalar() or 0,
        "total_exam_sessions": total_sessions.scalar() or 0,
        "completed_sessions": completed_sessions.scalar() or 0,
        "flagged_for_collusion": flagged_sessions.scalar() or 0,
        "avg_theta_all_students": round(avg_theta.scalar() or 0.0, 4),
    }


@router.get("/exam/{exam_id}", summary="Per-exam statistics")
async def get_exam_stats(
    exam_id: str,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        eid = uuid.UUID(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    exam = await db.get(Exam, eid)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    sessions_result = await db.execute(
        select(ExamSession).where(ExamSession.exam_id == eid)
    )
    sessions = sessions_result.scalars().all()
    completed = [s for s in sessions if s.status == "completed"]

    thetas = [s.theta_final for s in completed if s.theta_final is not None]
    avg_theta = sum(thetas) / len(thetas) if thetas else 0.0
    avg_items = sum(s.items_administered for s in completed) / len(completed) if completed else 0.0
    flagged = [s for s in completed if s.collusion_flag]

    # Grade distribution
    grade_dist: dict[str, int] = {}
    from src.ml.irt.model import IRTModel
    for s in completed:
        if s.theta_final is not None:
            grade = IRTModel.theta_to_grade(s.theta_final)
            grade_dist[grade] = grade_dist.get(grade, 0) + 1

    return {
        "exam_id": exam_id,
        "exam_title": exam.title,
        "subject": exam.subject,
        "total_attempts": len(sessions),
        "completed_attempts": len(completed),
        "avg_theta": round(avg_theta, 4),
        "avg_items_administered": round(avg_items, 1),
        "flagged_for_collusion": len(flagged),
        "grade_distribution": grade_dist,
        "thetas": [round(t, 3) for t in thetas],  # For histogram in frontend
    }


@router.get("/exam/{exam_id}/flags", summary="View flagged sessions for collusion")
async def get_flagged_sessions(
    exam_id: str,
    current_user: FacultyUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Returns all sessions flagged for potential collusion in this exam."""
    try:
        eid = uuid.UUID(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    result = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == eid,
            ExamSession.collusion_flag == True,
        ).order_by(ExamSession.collusion_probability.desc())
    )
    flagged = result.scalars().all()

    flagged_list = []
    for s in flagged:
        student = await db.get(User, s.student_id)
        flagged_list.append({
            "session_id": s.cat_session_id,
            "student_id": str(s.student_id),
            "student_name": student.full_name if student else "Unknown",
            "student_email": student.email if student else "Unknown",
            "collusion_probability": round(s.collusion_probability or 0, 4),
            "grade": s.grade,
            "items_administered": s.items_administered,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        })

    return {
        "exam_id": exam_id,
        "total_flagged": len(flagged_list),
        "flagged_sessions": flagged_list,
    }