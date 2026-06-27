from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from src.core.settings import settings

class Base(AsyncAttrs, DeclarativeBase): pass

engine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)

async def get_db_session():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    S = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with S() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback(); raise
        finally:
            await session.close()

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="student")  # student|faculty|admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ExamItem(Base):
    """A single question in the item bank."""
    __tablename__ = "exam_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(100), index=True)
    topic: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), default="mcq")  # mcq|open
    options: Mapped[Optional[dict]] = mapped_column(JSONB)  # MCQ choices
    correct_option: Mapped[Optional[int]] = mapped_column(Integer)
    irt_a: Mapped[float] = mapped_column(Float, default=1.0)
    irt_b: Mapped[float] = mapped_column(Float, default=0.0)
    irt_c: Mapped[float] = mapped_column(Float, default=0.25)
    irt_calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_adaptive: Mapped[bool] = mapped_column(Boolean, default=True)
    max_items: Mapped[int] = mapped_column(Integer, default=30)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|active|closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    exam_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exams.id"), index=True)
    cat_session_id: Mapped[str] = mapped_column(String(100))  # Redis key
    theta_final: Mapped[Optional[float]] = mapped_column(Float)
    theta_se_final: Mapped[Optional[float]] = mapped_column(Float)
    items_administered: Mapped[int] = mapped_column(Integer, default=0)
    score_percent: Mapped[Optional[float]] = mapped_column(Float)
    grade: Mapped[Optional[str]] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(20), default="active")
    collusion_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    collusion_probability: Mapped[Optional[float]] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class ItemResponse(Base):
    """Every response a student gives, stored for analysis."""
    __tablename__ = "item_responses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exam_sessions.id"), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exam_items.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    selected_option: Mapped[Optional[int]] = mapped_column(Integer)
    open_answer: Mapped[Optional[str]] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    time_taken_seconds: Mapped[float] = mapped_column(Float)
    theta_after: Mapped[Optional[float]] = mapped_column(Float)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())