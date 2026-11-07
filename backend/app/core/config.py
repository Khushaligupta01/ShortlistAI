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

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    FRONTEND_URL: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"

    SEED_RECRUITER_PASSWORD: str = "Recruiter@Demo2024!"
    SEED_CLIENT_PASSWORD: str = "Client@Demo2024!"
    SEED_DELIVERY_PASSWORD: str = "Delivery@Demo2024!"

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
