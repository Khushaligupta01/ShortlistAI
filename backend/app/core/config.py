from __future__ import annotations

import sys
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ShortlistAI"
    APP_ENV: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./shortlistai_dev.db"

    JWT_SECRET_KEY: str = "dev-only-secret-change-in-production-32ch"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    FRONTEND_URL: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"

    SEED_RECRUITER_PASSWORD: str = "Recruiter@Demo2024!"
    SEED_CLIENT_PASSWORD: str = "Client@Demo2024!"
    SEED_DELIVERY_PASSWORD: str = "Delivery@Demo2024!"

    # AI provider settings: default to 'fallback' (mock) for 100% local, self-contained offline evaluation without external API keys
    AI_PROVIDER: str = "fallback"
    AI_MODEL: str = "gpt-4o-mini"
    AI_API_KEY: str = ""
    AI_REQUEST_TIMEOUT: int = 30
    AI_MAX_RETRIES: int = 3
    AI_MAX_INPUT_TOKENS: int = 4000
    AI_MAX_OUTPUT_TOKENS: int = 1000

    # Phase 4: Storage & Processing Settings
    STORAGE_TYPE: str = "local"
    STORAGE_LOCAL_ROOT: str = "./storage/private"
    MAX_RESUME_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    MAX_BATCH_FILES_COUNT: int = 500
    MAX_BATCH_SIZE_BYTES: int = 250 * 1024 * 1024  # 250 MB
    WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    WORKER_CONCURRENCY: int = 5
    WORKER_LOCK_TIMEOUT_SECONDS: int = 600  # 10 minutes
    WORKER_MAX_ATTEMPTS: int = 3

    # Database connection pool settings (PostgreSQL)
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800

    def get_effective_ai_api_key(self) -> str:
        """Return configured AI_API_KEY or fallback to OPENAI_API_KEY from environment."""
        import os
        return self.AI_API_KEY or os.environ.get("AI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def validate_production(self) -> None:
        """Raise on insecure production defaults."""
        if self.APP_ENV == "production":
            if self.JWT_SECRET_KEY.startswith("dev-only"):
                raise ValueError("JWT_SECRET_KEY must be changed for production")
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")


settings = Settings()

if settings.APP_ENV == "production":
    settings.validate_production()
