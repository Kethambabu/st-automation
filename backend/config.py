"""
AI Test Platform — Application Configuration
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ────────────────────────────────────────────
    APP_NAME: str = "AI Test Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret-key"

    # ── Server ─────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ───────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/platform.db"

    # ── Redis ──────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Groq ───────────────────────────────────────────
    GROQ_API_KEY: str = ""  # Set via environment variable GROQ_API_KEY
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # ── Storage Paths ──────────────────────────────────
    UPLOAD_DIR: str = "./storage/uploads"
    EXTRACT_DIR: str = "./storage/extracted"
    GENERATED_DIR: str = "./storage/generated_tests"
    REPORTS_DIR: str = "./storage/reports"
    MAX_UPLOAD_SIZE_MB: int = 100

    # ── Logging ────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create all required storage directories."""
        for dir_path in [
            self.UPLOAD_DIR,
            self.EXTRACT_DIR,
            self.GENERATED_DIR,
            self.REPORTS_DIR,
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
