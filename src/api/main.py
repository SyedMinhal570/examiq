"""
src/api/main.py
───────────────
FastAPI application. This is what uvicorn runs.

uvicorn src.api.main:app --reload --port 8000
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.core.settings import settings
from src.db.models import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables + load SBERT model."""
    print(f"\n🚀 Starting {settings.app_name}...")

    # Create all DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables ready")

    print("SBERT will load on first plagiarism request.")

    print(f"✅ {settings.app_name} ready!\n")
    print("   Docs:   http://localhost:8000/docs")
    print("   Health: http://localhost:8000/health\n")

    yield

    print("👋 Shutting down ExamIQ...")


limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ExamIQ — Adaptive Exam Intelligence",
        version="1.0.0",
        description=(
            "AI-powered adaptive testing platform with IRT-based CAT engine "
            "and GNN anti-cheat detection. Built for ITU Lahore CE24."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
        ],
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID + timing middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next) -> Response:
        rid = str(uuid.uuid4())[:8]  # Short ID for readability
        request.state.request_id = rid
        t0 = time.monotonic()
        response = await call_next(request)
        ms = int((time.monotonic() - t0) * 1000)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time-Ms"] = str(ms)
        return response

    # Global exception handler — never expose stack traces in production
    @app.exception_handler(Exception)
    async def global_error(request: Request, exc: Exception) -> JSONResponse:
        import traceback
        if settings.debug:
            detail = traceback.format_exc()
        else:
            detail = "Internal server error. Please try again."
        return JSONResponse(status_code=500, content={"detail": detail})

    # Prometheus metrics at /metrics
    Instrumentator(
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")

    # ── Register all routes ───────────────────────────────────────
    from src.api.routes.auth      import router as auth_router
    from src.api.routes.exam      import router as exam_router
    from src.api.routes.items     import router as items_router
    from src.api.routes.analytics import router as analytics_router
    from src.api.routes.health    import router as health_router

    app.include_router(health_router)                                        # /health
    app.include_router(auth_router,      prefix="/api/v1/auth",      tags=["🔐 Auth"])
    app.include_router(exam_router,      prefix="/api/v1/exam",      tags=["📝 Exam"])
    app.include_router(items_router,     prefix="/api/v1/items",     tags=["📚 Items"])
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["📊 Analytics"])

    return app


app = create_app()