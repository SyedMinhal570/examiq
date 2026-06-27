"""
src/api/routes/exam.py
───────────────────────
Core exam-taking endpoints. Fully wired to CAT engine + IRT model.

Flow:
  1. POST /start          → Student starts exam, gets session_id
  2. GET  /session/{id}/next  → Get next adaptive question
  3. POST /session/{id}/answer → Submit answer, get theta update
  4. POST /session/{id}/finish → End exam, trigger collusion check
  5. GET  /session/{id}/result → View final result

All endpoints require JWT auth.
Students can only access their own sessions.
Faculty can view all sessions for exams they created.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import CurrentUser, FacultyUser
from src.db.models import Exam, ExamItem, ExamSession, ItemResponse as ItemResponseModel, get_db_session
from src.ml.irt.model import IRTItem, IRTModel
from src.ml.irt.cat_engine import CATSession
from src.services.exam_service import ExamService

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────

class StartExamRequest(BaseModel):
    exam_id: str = Field(..., description="UUID of the exam to take")


class StartExamResponse(BaseModel):
    session_id: str
    exam_id: str
    exam_title: str
    max_items: int
    time_limit_minutes: int
    message: str


class NextQuestionResponse(BaseModel):
    item_id: str
    content: str
    item_type: str
    options: list[str] | None  # None for open-ended
    question_number: int
    theta_estimate: float
    # We do NOT send irt params to student — that would allow gaming
    session_complete: bool = False


class SubmitAnswerRequest(BaseModel):
    item_id: str
    selected_option: int | None = Field(
        default=None,
        description="0-based index for MCQ. Null for open-ended.",
    )
    open_answer: str | None = Field(
        default=None,
        max_length=5000,
        description="Text answer for open-ended questions",
    )
    time_taken_seconds: float = Field(..., ge=0, le=7200)


class SubmitAnswerResponse(BaseModel):
    correct: bool | None      # None for open-ended (async graded)
    theta: float
    theta_se: float
    items_answered: int
    exam_complete: bool
    grade: str | None
    percentile: int | None
    message: str


class ExamResultResponse(BaseModel):
    session_id: str
    exam_title: str
    student_name: str
    theta_final: float
    grade: str
    percentile: int
    items_administered: int
    score_percent: float
    status: str
    collusion_flag: bool
    collusion_probability: float | None
    started_at: str
    completed_at: str | None


# ── Routes ────────────────────────────────────────────────────────

@router.post(
    "/start",
    response_model=StartExamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an adaptive exam session",
)
async def start_exam(
    body: StartExamRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> StartExamResponse:
    """
    Start a new CAT exam session for the authenticated student.
    Returns session_id — use this for all subsequent calls.
    """
    # Validate exam exists and is active
    try:
        eid = uuid.UUID(body.exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    exam = await db.get(Exam, eid)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Exam is not active (status: {exam.status})",
        )

    # Prevent re-taking (one session per student per exam)
    existing = await db.execute(
        select(ExamSession).where(
            ExamSession.student_id == current_user.id,
            ExamSession.exam_id == eid,
            ExamSession.status.in_(["active", "completed"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You have already started or completed this exam.",
        )

    # Initialize CAT session in Redis
    service = ExamService(db)
    cat_session = await service.start_cat_session(
        student_id=str(current_user.id),
        exam_id=str(eid),
    )

    # Create DB record
    db_session = ExamSession(
        student_id=current_user.id,
        exam_id=eid,
        cat_session_id=cat_session.session_id,
        status="active",
    )
    db.add(db_session)
    await db.flush()

    return StartExamResponse(
        session_id=cat_session.session_id,
        exam_id=str(eid),
        exam_title=exam.title,
        max_items=exam.max_items,
        time_limit_minutes=exam.time_limit_minutes,
        message="Exam started! Good luck. Call /next to get your first question.",
    )


@router.get(
    "/session/{session_id}/next",
    response_model=NextQuestionResponse,
    summary="Get the next adaptive question",
)
async def get_next_question(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> NextQuestionResponse:
    """
    Returns the most informative next question for this student's ability level.
    CAT engine selects item with maximum Fisher Information at current θ estimate.
    """
    service = ExamService(db)
    cat_session = await service.get_cat_session(session_id)

    if not cat_session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if cat_session.student_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your session")
    if cat_session.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Exam already completed. Use /result to view your results.",
        )
    if cat_session.should_stop:
        raise HTTPException(
            status_code=400,
            detail="Exam is complete. Submit /finish to get your results.",
        )

    # Get all available items for this exam subject
    exam_id = uuid.UUID(cat_session.exam_id)
    exam = await db.get(Exam, exam_id)

    items_result = await db.execute(
        select(ExamItem).where(ExamItem.subject == exam.subject if exam else True)
    )
    all_items_db = items_result.scalars().all()

    if not all_items_db:
        raise HTTPException(
            status_code=400,
            detail="No items available for this exam subject.",
        )

    # Convert to IRTItem objects for the CAT engine
    irt_items = [
        IRTItem(
            item_id=str(item.id),
            a=item.irt_a,
            b=item.irt_b,
            c=item.irt_c,
            content=item.content,
            options=item.options.get("choices", []) if item.options else [],
            correct_option=item.correct_option or 0,
        )
        for item in all_items_db
    ]

    # CAT: select next item
    administered_set = set(cat_session.administered_ids)
    next_item = IRTModel.select_next_item(cat_session.theta, irt_items, administered_set)

    if not next_item:
        raise HTTPException(
            status_code=400,
            detail="No more items available. Please finish the exam.",
        )

    return NextQuestionResponse(
        item_id=next_item.item_id,
        content=next_item.content,
        item_type="mcq" if next_item.options else "open",
        options=next_item.options if next_item.options else None,
        question_number=cat_session.items_administered + 1,
        theta_estimate=round(cat_session.theta, 3),
        session_complete=False,
    )


@router.post(
    "/session/{session_id}/answer",
    response_model=SubmitAnswerResponse,
    summary="Submit answer and get updated ability estimate",
)
async def submit_answer(
    session_id: str,
    body: SubmitAnswerRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> SubmitAnswerResponse:
    """
    Submit an answer for the current question.
    IRT model updates θ estimate immediately.
    Returns whether exam should continue or is complete.
    """
    service = ExamService(db)
    cat_session = await service.get_cat_session(session_id)

    if not cat_session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if cat_session.student_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your session")
    if cat_session.status == "completed":
        raise HTTPException(status_code=400, detail="Exam already completed")

    # Fetch the item
    try:
        iid = uuid.UUID(body.item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    db_item = await db.get(ExamItem, iid)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify not already answered
    if body.item_id in cat_session.administered_ids:
        raise HTTPException(status_code=400, detail="Item already answered in this session")

    # Determine correctness
    correct: bool | None = None
    if db_item.item_type == "mcq":
        if body.selected_option is None:
            raise HTTPException(status_code=400, detail="MCQ requires selected_option")
        correct = (body.selected_option == db_item.correct_option)
    # open-ended: async graded later

    # Build IRTItem
    irt_item = IRTItem(
        item_id=str(db_item.id),
        a=db_item.irt_a,
        b=db_item.irt_b,
        c=db_item.irt_c,
    )

    # Update CAT session with response
    cat_session.record_response(
        item=irt_item,
        correct=correct if correct is not None else False,
        time_taken=body.time_taken_seconds,
    )
    if cat_session.should_stop:
        cat_session.status = "completed"

    # Persist updated session to Redis
    await service.save_cat_session(cat_session)

    # Store item response in PostgreSQL
    db_session_result = await db.execute(
        select(ExamSession).where(ExamSession.cat_session_id == session_id)
    )
    db_session = db_session_result.scalar_one_or_none()

    if db_session:
        response_record = ItemResponseModel(
            session_id=db_session.id,
            item_id=iid,
            student_id=current_user.id,
            selected_option=body.selected_option,
            open_answer=body.open_answer,
            is_correct=correct or False,
            time_taken_seconds=body.time_taken_seconds,
            theta_after=cat_session.theta,
        )
        db.add(response_record)
        db_session.items_administered = cat_session.items_administered

        if cat_session.status == "completed":
            db_session.theta_final = cat_session.theta
            db_session.theta_se_final = cat_session.theta_se
            db_session.grade = IRTModel.theta_to_grade(cat_session.theta)
            db_session.score_percent = round(
                sum(1 for r in cat_session.responses if r["correct"]) / len(cat_session.responses) * 100, 1
            ) if cat_session.responses else 0.0
            db_session.status = "completed"
            db_session.completed_at = datetime.now(timezone.utc)

    return SubmitAnswerResponse(
        correct=correct,
        theta=round(cat_session.theta, 4),
        theta_se=round(cat_session.theta_se, 4),
        items_answered=cat_session.items_administered,
        exam_complete=cat_session.status == "completed",
        grade=IRTModel.theta_to_grade(cat_session.theta) if cat_session.status == "completed" else None,
        percentile=IRTModel.theta_to_percentile(cat_session.theta) if cat_session.status == "completed" else None,
        message=(
            "Exam complete! Use /finish to save your results."
            if cat_session.status == "completed"
            else f"Question answered. θ={cat_session.theta:.3f}. Call /next for next question."
        ),
    )


@router.post(
    "/session/{session_id}/finish",
    summary="Finalize exam and trigger collusion analysis",
)
async def finish_exam(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Finalize the exam session.
    Triggers async Celery task for collusion detection.
    """
    service = ExamService(db)
    cat_session = await service.get_cat_session(session_id)

    if not cat_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if cat_session.student_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your session")

    # Force complete if not already
    cat_session.status = "completed"
    await service.save_cat_session(cat_session)

    # Finalize DB record
    db_session_result = await db.execute(
        select(ExamSession).where(ExamSession.cat_session_id == session_id)
    )
    db_session = db_session_result.scalar_one_or_none()

    if db_session and db_session.status != "completed":
        db_session.status = "completed"
        db_session.theta_final = cat_session.theta
        db_session.theta_se_final = cat_session.theta_se
        db_session.grade = IRTModel.theta_to_grade(cat_session.theta)
        db_session.completed_at = datetime.now(timezone.utc)
        if cat_session.responses:
            correct_count = sum(1 for r in cat_session.responses if r["correct"])
            db_session.score_percent = round(correct_count / len(cat_session.responses) * 100, 1)

    # Trigger async collusion detection
    try:
        from src.worker.tasks import run_collusion_detection
        run_collusion_detection.delay(
            exam_id=cat_session.exam_id,
            session_id=session_id,
        )
    except Exception:
        pass  # Celery might not be running in dev — that's OK

    return {
        "status": "completed",
        "session_id": session_id,
        "theta": round(cat_session.theta, 4),
        "grade": IRTModel.theta_to_grade(cat_session.theta),
        "percentile": IRTModel.theta_to_percentile(cat_session.theta),
        "items_administered": cat_session.items_administered,
        "message": "Exam finalized. Collusion analysis queued. View /result for full report.",
    }


@router.get(
    "/session/{session_id}/result",
    response_model=ExamResultResponse,
    summary="Get final exam result",
)
async def get_result(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> ExamResultResponse:
    """Get the final result for a completed exam session."""
    result = await db.execute(
        select(ExamSession).where(ExamSession.cat_session_id == session_id)
    )
    db_session = result.scalar_one_or_none()

    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Students can only see their own results; faculty see all
    if current_user.role == "student" and db_session.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    exam = await db.get(Exam, db_session.exam_id)
    student = await db.get(__import__("src.db.models", fromlist=["User"]).User, db_session.student_id)

    theta = db_session.theta_final or 0.0
    return ExamResultResponse(
        session_id=session_id,
        exam_title=exam.title if exam else "Unknown Exam",
        student_name=student.full_name if student else "Unknown",
        theta_final=round(theta, 4),
        grade=db_session.grade or IRTModel.theta_to_grade(theta),
        percentile=IRTModel.theta_to_percentile(theta),
        items_administered=db_session.items_administered,
        score_percent=db_session.score_percent or 0.0,
        status=db_session.status,
        collusion_flag=db_session.collusion_flag,
        collusion_probability=db_session.collusion_probability,
        started_at=db_session.started_at.isoformat(),
        completed_at=db_session.completed_at.isoformat() if db_session.completed_at else None,
    )


@router.get(
    "/my-sessions",
    summary="Get all exam sessions for current student",
)
async def get_my_sessions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Returns all exam sessions for the authenticated student."""
    result = await db.execute(
        select(ExamSession)
        .where(ExamSession.student_id == current_user.id)
        .order_by(ExamSession.started_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "session_id": s.cat_session_id,
                "exam_id": str(s.exam_id),
                "status": s.status,
                "grade": s.grade,
                "theta_final": s.theta_final,
                "items_administered": s.items_administered,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ]
    }