"""
AI Test Platform — Test Case Schemas
"""

from datetime import datetime
from pydantic import BaseModel


class TestCaseResponse(BaseModel):
    """Schema for test case API responses."""
    id: str
    project_id: str
    target_file: str
    target_function: str
    test_type: str
    test_code: str
    status: str
    confidence_score: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TestGenerateRequest(BaseModel):
    """Schema for test generation request."""
    test_types: list[str] = ["unit", "edge_case"]
    max_tests_per_function: int = 3
