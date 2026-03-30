"""
AI Test Platform — Improved Pytest Python API Runner

Directly uses pytest's Python API instead of subprocess for:
- Better control and error handling
- Direct access to detailed results
- No subprocess overhead
- Better testability
"""

import sys
import tempfile
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import pytest
from _pytest.config import Config
from _pytest.main import Session
from _pytest.reports import TestReport

from core.executor.test_models import (
    IndividualTestResult,
    TestRunSummary,
    TestFailureInfo,
    TestExecutionMetrics,
    TestOutcome,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class PytestHookCollector:
    """
    Hook collector to capture pytest results in real-time.
    
    Implements pytest hook system to intercept test results.
    """
    
    def __init__(self):
        self.test_results: Dict[str, IndividualTestResult] = {}
        self.session_start_time: Optional[float] = None
        self.session_end_time: Optional[float] = None
        self.session: Optional[Session] = None
    
    def pytest_runtest_logreport(self, report: TestReport):
        """Called after each test phase (setup, call, teardown)."""
        # We only care about the final call report
        if report.when == "call":
            test_id = report.nodeid
            
            # Map pytest outcome to our TestOutcome
            outcome_map = {
                "passed": TestOutcome.PASSED,
                "failed": TestOutcome.FAILED,
                "error": TestOutcome.ERROR,
                "skipped": TestOutcome.SKIPPED,
            }
            outcome = outcome_map.get(report.outcome, TestOutcome.ERROR)
            
            # Extract error info if failed
            failure = None
            if report.outcome in ("failed", "error"):
                failure_info = self._extract_failure_info(report)
                failure = TestFailureInfo(**failure_info)
            
            # Create result
            result = IndividualTestResult(
                test_id=test_id,
                test_name=test_id.split("::")[-1],
                outcome=outcome,
                failure=failure,
                metrics=TestExecutionMetrics(
                    duration_ms=report.duration * 1000,
                ),
            )
            
            self.test_results[test_id] = result
            logger.debug(f"Captured result for {test_id}: {outcome.value}")
    
    def _extract_failure_info(self, report: TestReport) -> Dict[str, str]:
        """Extract failure details from pytest report."""
        failure_info = {
            "type": "Unknown",
            "assertion_message": str(report.outcome),
            "traceback": None,
        }
        
        if report.longrepr:
            # Try to extract the assertion message
            longrepr_str = str(report.longrepr)
            lines = longrepr_str.split('\n')
            
            # The assertion is usually the last line before the summary
            if lines:
                # Get last non-empty line
                for line in reversed(lines):
                    if line.strip():
                        failure_info["assertion_message"] = line.strip()
                        break
            
            failure_info["traceback"] = longrepr_str[:500]  # Limit to 500 chars
        
        return failure_info


class PytestApiRunnerV2:
    """
    Executes pytest using the Python API.
    
    Features:
    - Direct API access (no subprocess)
    - Real-time hook capture
    - Detailed error information
    - Better performance
    
    Usage:
        runner = PytestApiRunnerV2()
        summary = runner.run_tests(
            test_file=Path("/tmp/test_generated.py"),
            base_url="http://localhost:8000"
        )
    """
    
    def run_tests(
        self,
        test_file: Path,
        timeout: int = 300,
        verbose: bool = True,
        capture_output: bool = True,
        cwd: Path | None = None,
    ) -> TestRunSummary:
        """
        Execute a pytest test file using the Python API.
        
        Args:
            test_file: Path to the pytest file to execute
            timeout: Pytest timeout in seconds
            verbose: Enable verbose output
            capture_output: Capture test output
            
        Returns:
            TestRunSummary with complete results
        """
        if not test_file.exists():
            logger.error(f"Test file not found: {test_file}")
            raise FileNotFoundError(f"Test file not found: {test_file}")

        # pytest args should always use an absolute path.
        # This avoids "file not found" when we temporarily chdir into the project directory.
        try:
            test_file_abs = test_file.resolve(strict=True)
        except Exception:
            test_file_abs = test_file.resolve(strict=False)
        
        logger.info(
            f"Running tests from {test_file_abs}",
            cwd=str(cwd) if cwd else None,
        )
        
        # Create hook collector
        hook_collector = PytestHookCollector()
        
        # Build pytest arguments
        # NOTE: We only pass "--timeout=..." if the corresponding pytest plugin
        # is installed. Otherwise pytest will fail with "unrecognized arguments".
        timeout_arg = None
        try:
            import pytest_timeout  # noqa: F401
            timeout_arg = f"--timeout={timeout}"
        except Exception:
            timeout_arg = None

        pytest_args = [
            str(test_file_abs),
            "-v" if verbose else "-q",
            timeout_arg,
            "--tb=short",
            "-o", "addopts=",  # Disable any file watching from addopts
        ]
        pytest_args = [arg for arg in pytest_args if arg is not None]
        
        if not capture_output:
            pytest_args.append("-s")  # Don't capture output
        
        # Execute pytest
        exit_code = None
        start_cwd = None
        try:
            if cwd is not None:
                start_cwd = os.getcwd()
                os.chdir(str(cwd))
            # Add our hook to pytest
            pytest.main(pytest_args, plugins=[hook_collector])
            exit_code = 0  # Successful execution (even if tests failed)
        except SystemExit as e:
            exit_code = e.code
        except Exception as e:
            logger.error(f"Pytest execution failed: {e}", exc_info=True)
            exit_code = 1
        finally:
            if start_cwd is not None:
                os.chdir(start_cwd)
        
        # Build summary from collected results
        summary = self._build_summary(
            hook_collector.test_results,
            exit_code,
            test_file_abs,
        )
        
        return summary
    
    def _build_summary(
        self,
        results: Dict[str, IndividualTestResult],
        exit_code: int,
        test_file: Path,
    ) -> TestRunSummary:
        """Build aggregated summary from individual test results."""
        from uuid import uuid4
        
        passed = sum(1 for r in results.values() if r.outcome == TestOutcome.PASSED)
        failed = sum(1 for r in results.values() if r.outcome == TestOutcome.FAILED)
        errors = sum(1 for r in results.values() if r.outcome == TestOutcome.ERROR)
        skipped = sum(1 for r in results.values() if r.outcome == TestOutcome.SKIPPED)
        
        total = len(results)
        
        summary = TestRunSummary(
            run_id=str(uuid4()),
            project_id="unknown",  # Will be set by caller
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration_seconds=0.0,  # TODO: calculate from results
            results=list(results.values()),
        )
        
        logger.info(
            f"Test summary: {total} total, {passed} passed, {failed} failed, {errors} errors"
        )
        
        return summary


# ============================================================================
# Backward Compatibility Wrapper
# ============================================================================

from dataclasses import dataclass, field
from core.executor.pytest_runner import PytestRunner as OldPytestRunner

# The old runner still works, but we can enhance it with better error handling
# For now, keep backward compatibility by keeping the old class name


class PytestRunner(OldPytestRunner):
    """
    Enhanced pytest runner with better error handling.
    
    This extends the old runner with improvements while maintaining
    backward compatibility.
    """
    
    def __init__(self):
        super().__init__()
        self.api_runner = PytestApiRunnerV2()
    
    def run_tests_api(
        self,
        test_dir: Path,
        timeout: int = 300,
    ) -> TestRunSummary:
        """
        Execute tests using pytest Python API (new preferred method).
        
        Args:
            test_dir: Directory containing test files
            timeout: Execution timeout in seconds
            
        Returns:
            TestRunSummary with detailed results
        """
        test_file = test_dir / "test_markdown_generated.py"
        
        try:
            summary = self.api_runner.run_tests(
                test_file=test_file,
                timeout=timeout,
            )
            logger.info(
                "Pytest execution completed",
                total=summary.total,
                passed=summary.passed,
                failed=summary.failed,
                errors=summary.errors,
            )
            return summary
        except Exception as e:
            logger.error(f"Pytest execution failed: {e}", exc_info=True)
            raise
