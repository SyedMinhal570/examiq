"""
src/services/exam_service.py
─────────────────────────────
Business logic layer. Sits between API routes and ML models.
Handles Redis session storage and database queries.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.ml.irt.cat_engine import CATSession


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


class ExamService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def start_cat_session(self, student_id: str, exam_id: str) -> CATSession:
        """Create a new CAT session and store in Redis."""
        session = CATSession(
            session_id=str(uuid.uuid4()),
            student_id=student_id,
            exam_id=exam_id,
        )
        await self.save_cat_session(session)
        return session

    async def get_cat_session(self, session_id: str) -> CATSession | None:
        """Load CAT session from Redis."""
        r = await self._get_redis()
        data = await r.get(f"cat_session:{session_id}")
        if not data:
            return None
        d = json.loads(data)
        return CATSession(**d)

    async def save_cat_session(self, session: CATSession) -> None:
        """Persist CAT session to Redis with 3-hour TTL."""
        r = await self._get_redis()
        await r.setex(
            f"cat_session:{session.session_id}",
            10800,  # 3 hours
            json.dumps(asdict(session)),
        )

    async def delete_cat_session(self, session_id: str) -> None:
        r = await self._get_redis()
        await r.delete(f"cat_session:{session_id}")