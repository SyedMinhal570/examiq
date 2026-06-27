"""src/core/settings.py"""
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ExamIQ"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str = "dev-secret-change-in-prod-minimum-32-chars-long"

    # Database
    database_url: str = "postgresql+asyncpg://examiq:examiq123@localhost:5432/examiq"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret_key: str = "jwt-secret-change-in-prod-minimum-32-chars-long"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # ML Models
    sbert_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gnn_model_path: str = "./data/models/collusion_gnn.pt"

    # Anti-cheat thresholds
    similarity_threshold: float = 0.85
    timing_zscore_threshold: float = 3.0

    # IRT / CAT
    min_items_before_estimate: int = 5
    max_items_per_exam: int = 30
    theta_convergence_threshold: float = 0.05

    # Rate limits
    rate_limit_exam: str = "30/minute"
    rate_limit_api: str = "60/minute"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()