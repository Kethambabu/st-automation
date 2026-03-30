"""
AI Test Platform — Improved Test Data Models

Type-safe, validated data structures for the test execution pipeline.
Replaces fragile dict-based representations with proper Pydantic models.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from enum import Enum
import json
from pydantic import BaseModel, Field, validator


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class TestOutcome(str, Enum):
    """Possible test outcomes."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


# ============================================================================
# INPUT MODELS (from Markdown)
# ============================================================================

class ParsedTestCase(BaseModel):
    """
    A single test case parsed from Markdown.
    
    This is the **intermediate representation** between Markdown and execution.
    Includes validation to catch problems early.
    """
    
    # Required fields
    name: str = Field(..., min_length=1, max_length=255)
    endpoint: str = Field(..., min_length=1, max_length=1000)
    
    # Optional fields with sensible defaults
    method: HTTPMethod = Field(default=HTTPMethod.GET)
    input_data: Optional[Dict[str, Any]] = Field(default=None)
    expected_status: int = Field(default=200, ge=100, le=599)
    description: Optional[str] = Field(default=None, max_length=2000)
    
    @validator('endpoint')
    def validate_endpoint(cls, v: str) -> str:
        """Ensure endpoint starts with /"""
        v = v.strip()
        if not v.startswith('/'):
            v = '/' + v
        return v
    
    @validator('method', pre=True)
    def parse_method(cls, v: Any) -> HTTPMethod:
        """Handle method as string or enum"""
        if isinstance(v, str):
            return HTTPMethod[v.upper()]
        return v
    
    class Config:
        use_enum_values = False  # Keep as Enum, not string


class ParsedTestSpecification(BaseModel):
    """
    Complete parsed Markdown test specification.
    Contains all test cases extracted from one Markdown document.
    """
    
    test_cases: List[ParsedTestCase] = Field(default_factory=list)
    raw_content: str = Field(default="")
    parsing_errors: List[str] = Field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if parsing was completely successful."""
        return len(self.parsing_errors) == 0 and len(self.test_cases) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there were non-fatal parsing issues."""
        return len(self.parsing_errors) > 0


# ============================================================================
# EXECUTION MODELS (pytest code generation)
# ============================================================================

class GeneratedTest(BaseModel):
    """
    A test case ready to be converted into pytest code.
    Includes metadata needed for code generation.
    """
    
    test_id: str = Field(...)  # UUID of the test case
    test_name: str = Field(...)  # Human-readable name
    function_name: str = Field(...)  # Safe Python function name: test_<id>_<name>
    
    endpoint: str = Field(...)
    method: HTTPMethod = Field(...)
    input_data: Optional[Dict[str, Any]] = Field(default=None)
    expected_status: int = Field(...)
    
    @staticmethod
    def from_parsed(parsed: ParsedTestCase, test_id: str) -> "GeneratedTest":
        """Convert a ParsedTestCase into a GeneratedTest with proper naming."""
        from core.executor.utils import sanitize_test_name
        
        function_name = sanitize_test_name(test_id, parsed.name)
        
        return GeneratedTest(
            test_id=test_id,
            test_name=parsed.name,
            function_name=function_name,
            endpoint=parsed.endpoint,
            method=parsed.method,
            input_data=parsed.input_data,
            expected_status=parsed.expected_status,
        )


class TargetServer(BaseModel):
    """Configuration for the target server being tested."""
    
    base_url: str = Field(...)
    timeout_seconds: float = Field(default=30.0, gt=0)
    verify_ssl: bool = Field(default=True)


# ============================================================================
# RESULT MODELS (from pytest execution)
# ============================================================================

class TestExecutionMetrics(BaseModel):
    """Timing and execution metrics for a single test."""
    
    duration_ms: float = Field(default=0.0, ge=0)
    start_time: Optional[str] = Field(default=None)  # ISO 8601
    end_time: Optional[str] = Field(default=None)    # ISO 8601


class TestFailureInfo(BaseModel):
    """Detailed failure information."""
    
    assertion_message: str = Field(...)
    traceback: Optional[str] = Field(default=None)
    type: str = Field(default="AssertionError")  # AssertionError, TimeoutError, etc.
    

class IndividualTestResult(BaseModel):
    """
    Result of executing a single test case.
    Replaces the dict-based results from the old pipeline.
    """
    
    test_id: str = Field(...)
    test_name: str = Field(...)
    outcome: TestOutcome = Field(...)
    metrics: TestExecutionMetrics = Field(default_factory=TestExecutionMetrics)
    
    # Optional detailed failure info
    failure: Optional[TestFailureInfo] = Field(default=None)
    
    # Captured output
    stdout: Optional[str] = Field(default=None)
    stderr: Optional[str] = Field(default=None)
    
    @property
    def passed(self) -> bool:
        return self.outcome == TestOutcome.PASSED
    
    @property
    def failed(self) -> bool:
        return self.outcome in (TestOutcome.FAILED, TestOutcome.ERROR)


class TestRunSummary(BaseModel):
    """
    Aggregated statistics for an entire test run.
    Similar to the old TestRun model but with cleaner structure.
    """
    
    run_id: str = Field(...)
    project_id: str = Field(...)
    
    total: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    
    duration_seconds: float = Field(default=0.0, ge=0)
    
    # Detailed results
    results: List[IndividualTestResult] = Field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100.0
    
    @property
    def status(self) -> str:
        """Determine overall status."""
        if self.total == 0:
            return "NO_TESTS"
        elif self.failed > 0 or self.errors > 0:
            return "FAILED"
        else:
            return "PASSED"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for database storage."""
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "duration_seconds": self.duration_seconds,
            "pass_rate": self.pass_rate,
            "status": self.status,
        }


# ============================================================================
# CONFIGURATION MODELS
# ============================================================================

class ExecutionConfig(BaseModel):
    """Configuration for the test execution pipeline."""
    
    # Server configuration
    target_server: TargetServer = Field(...)
    
    # Pytest configuration
    pytest_timeout_seconds: int = Field(default=300, gt=0)
    pytest_verbose: bool = Field(default=True)
    capture_output: bool = Field(default=True)
    
    # Execution options
    stop_on_first_failure: bool = Field(default=False)
    fail_on_error: bool = Field(default=True)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    class Config:
        use_enum_values = False
