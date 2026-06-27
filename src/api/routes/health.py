"""src/api/routes/health.py"""
from __future__ import annotations
import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from src.core.settings import settings
from src.db.models import engine as db_engine

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}


@router.get("/health/ready", tags=["Health"])
async def readiness() -> JSONResponse:
    checks: dict = {}
    healthy = True

    # Check PostgreSQL
    try:
        async with db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgresql"] = "ok"
    except Exception as e:
        checks["postgresql"] = f"error: {e}"
        healthy = False

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "healthy" if healthy else "degraded", "checks": checks, "ts": time.time()},
    )