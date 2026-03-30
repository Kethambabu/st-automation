"""
AI Test Platform — Result Schemas
"""

from datetime import datetime
from pydantic import BaseModel


class TestResultResponse(BaseModel):
    """Schema for individual test result."""
    id: str
    test_case_id: str
    status: str
    stdout: str | None = None
    stderr: str | None = None
    error_message: str | None = None
    duration_seconds: float | None = None

    class Config:
        from_attributes = True


class TestRunResponse(BaseModel):
    """Schema for test run summary."""
    id: str
    project_id: str
    status: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    coverage_percent: float | None = None
    duration_seconds: float | None = None
    executed_at: datetime
    results: list[TestResultResponse] = []

    class Config:
        from_attributes = True


class ExecutionRequest(BaseModel):
    """Schema for test execution request."""
    test_case_ids: list[str] | None = None  # None = run all
    with_coverage: bool = True
    markdown_content: str | None = None  # Allow passing raw markdown for execution
    target_base_url: str | None = None  # Override default base URL for tests (e.g., http://localhost:9000)

