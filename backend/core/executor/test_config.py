"""
Test Execution Configuration

Centralized settings for test execution pipeline.
Prevents hardcoded URLs and makes deployment easier.

Uses Pydantic v2 with SettingsConfigDict for proper environment variable handling.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal


class TestExecutionConfig(BaseSettings):
    """Configuration for test execution with Pydantic v2."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars not defined here (fixes Pydantic v2 validation)
        case_sensitive=False,  # Allow TEST_EXEC_TARGET_BASE_URL or test_exec_target_base_url
    )
    
    # Server Configuration
    target_base_url: str = Field(
        default="http://127.0.0.1:8000",
        description="Base URL for API tests. Endpoints should be absolute paths like /health or /api/v1/health",
        validation_alias="TEST_EXEC_TARGET_BASE_URL",
    )
    
    # Pytest Configuration
    pytest_timeout_seconds: int = Field(
        default=300,
        ge=1,
        description="Timeout (seconds) for pytest execution.",
        validation_alias="TEST_EXEC_PYTEST_TIMEOUT_SECONDS",
    )
    
    httpx_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Timeout (seconds) for httpx http calls.",
        validation_alias="TEST_EXEC_HTTPX_TIMEOUT_SECONDS",
    )
    
    # Execution Settings
    capture_output: bool = Field(
        default=True,
        description="Capture stdout/stderr during test execution.",
        validation_alias="TEST_EXEC_CAPTURE_OUTPUT",
    )
    
    verbose: bool = Field(
        default=True,
        description="Enable verbose logging during test execution.",
        validation_alias="TEST_EXEC_VERBOSE",
    )
    
    # LLM Configuration
    groq_api_key: Optional[str] = Field(
        default=None,
        description="Groq API key for LLM-based test generation.",
        validation_alias="GROQ_API_KEY",
    )
    
    # Environment Configuration
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment.",
        validation_alias="APP_ENV",
    )
    
    # Debug Configuration
    debug: bool = Field(
        default=False,
        description="Enable debug mode with additional logging.",
        validation_alias="DEBUG",
    )


# Global singleton instance
_config: Optional[TestExecutionConfig] = None


def get_test_config() -> TestExecutionConfig:
    """Get global test execution configuration."""
    global _config
    if _config is None:
        _config = TestExecutionConfig()
    return _config


def set_test_config(config: TestExecutionConfig):
    """Override global test configuration (useful for testing)."""
    global _config
    _config = config
