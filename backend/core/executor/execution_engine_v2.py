"""
AI Test Platform — Improved Execution Engine

Clean, refactored execution pipeline with proper error handling,
logging, and data flow.
"""

import uuid
import socket
import subprocess
import sys
import time
import re
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project
from models.test_case import TestCase
from models.test_result import TestRun, TestResult
from core.executor.test_models import (
    ParsedTestSpecification,
    GeneratedTest,
    TestRunSummary,
    IndividualTestResult,
    TestOutcome,
    ExecutionConfig,
    TargetServer,
)
from core.executor.markdown_parser_v2 import MarkdownTestParserV2
from core.executor.pytest_code_generator import PytestCodeGeneratorV2
from core.executor.pytest_api_runner import PytestApiRunnerV2
from config import get_settings
from utils.logger import get_logger

try:
    import httpx
except ImportError:
    httpx = None

logger = get_logger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class TestExecutionError(Exception):
    """Base exception for test execution."""
    pass


class MarkdownParseError(TestExecutionError):
    """Failed to parse markdown test specification."""
    pass


class CodeGenerationError(TestExecutionError):
    """Failed to generate valid pytest code."""
    pass


class PytestExecutionError(TestExecutionError):
    """Pytest execution failed."""
    pass


# ============================================================================
# HELPER FUNCTIONS FOR SERVER LIFECYCLE
# ============================================================================

def find_free_port() -> int:
    """
    Find an available port on localhost by binding to port 0.
    
    Returns:
        An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _find_entry_point(project_dir: Path) -> Optional[Tuple[str, str]]:
    """
    Detect the entry point of an uploaded project.
    
    Searches for common entry point files (main.py, app.py, etc.) and
    looks for patterns indicating FastAPI, Flask, or uvicorn applications.
    
    Handles nested project structures by auto-entering single subdirectories.
    
    Args:
        project_dir: Root directory of the uploaded project.
        
    Returns:
        Tuple of (module_name, app_variable) e.g. ("main", "app"),
        or None if no entry point found.
        
    Example:
        >>> _find_entry_point(Path("/tmp/my_project"))
        ("main", "app")
    """
    # If the directory contains a single subdirectory only (common in zip extracts),
    # auto-enter it to find the actual project root
    effective_dir = project_dir
    try:
        entries = list(project_dir.iterdir())
        dirs = [e for e in entries if e.is_dir() and not e.name.startswith('.')]
        files = [e for e in entries if e.is_file()]
        
        # If only one subdirectory and no Python files in root, enter the subdirectory
        if len(dirs) == 1 and len(files) == 0:
            effective_dir = dirs[0]
            logger.debug(
                f"Auto-entering single subdirectory: {effective_dir.name}"
            )
    except Exception as e:
        logger.debug(f"Error checking for subdirectory structure: {e}")
    
    candidates = ["main.py", "app.py", "run.py", "server.py", "asgi.py", "wsgi.py"]
    
    # Pattern: regex to search for, and the app variable name to use
    app_patterns = [
        (r'app\s*=\s*FastAPI\(', "app"),
        (r'app\s*=\s*Flask\(', "app"),
        (r'application\s*=\s*FastAPI\(', "application"),
        (r'application\s*=\s*Flask\(', "application"),
        (r'app\s*=\s*Starlette\(', "app"),
        (r'app\s*=\s*Quart\(', "app"),
    ]
    
    for candidate in candidates:
        candidate_path = effective_dir / candidate
        if not candidate_path.exists():
            continue
        
        try:
            text = candidate_path.read_text(encoding="utf-8", errors="ignore")
            for pattern, var_name in app_patterns:
                if re.search(pattern, text):
                    module_name = candidate[:-3]  # strip .py extension
                    logger.debug(
                        f"Found entry point: {module_name}:{var_name} "
                        f"(pattern matched in {candidate})"
                    )
                    return (module_name, var_name)
        except Exception as e:
            logger.warning(f"Error reading {candidate}: {e}")
            continue
    
    logger.debug(
        f"No entry point found in {effective_dir}. "
        f"Searched: {candidates}"
    )
    return None




class ImprovedTestExecutionEngine:
    """
    Orchestrates the complete test execution pipeline.
    
    Pipeline:
    1. Parse Markdown specification → ParsedTestSpecification
    2. Generate pytest code → Python test file
    3. Execute pytest → TestRunSummary
    4. Save results to database
    5. Return aggregated statistics
    
    Features:
    - Type-safe models throughout
    - Structured error handling
    - Comprehensive logging at each step
    - Clean separation of concerns
    - Easy to test and debug
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or self._default_config()
        self.parser = MarkdownTestParserV2()
        self.code_generator = PytestCodeGeneratorV2()
        self.pytest_runner = PytestApiRunnerV2()
    
    @staticmethod
    def _default_config() -> ExecutionConfig:
        """Return default execution configuration."""
        return ExecutionConfig(
            target_server=TargetServer(base_url="http://127.0.0.1:8000"),
            pytest_timeout_seconds=300,
            pytest_verbose=True,
        )
    
    async def execute_markdown_tests(
        self,
        project_id: str,
        markdown_content: str,
        db: AsyncSession,
        config: Optional[ExecutionConfig] = None,
    ) -> Dict[str, Any]:
        """
        Execute markdown test specification end-to-end.
        
        Args:
            project_id: Project ID for tracking
            markdown_content: Raw markdown test specification
            db: Database session for saving results
            config: Optional execution configuration
            
        Returns:
            Dictionary with execution summary: {
                "success": bool,
                "summary": TestRunSummary dict,
                "errors": [str],
                "run_id": str,
            }
        """
        run_id = str(uuid.uuid4())
        config = config or self.config
        errors: List[str] = []
        
        logger.info(f"Starting test execution for project {project_id}")
        
        try:
            # Step 1: Verify project exists
            project = await self._get_project(project_id, db)
            if not project:
                raise TestExecutionError(f"Project {project_id} not found")
            
            logger.info("✓ Project verified")
            project_dir = Path(project.storage_path) if project.storage_path else None
            
            # Step 2: Parse Markdown
            parsed_spec = await self._parse_markdown(markdown_content)
            if not parsed_spec.test_cases:
                raise MarkdownParseError("No valid test cases found in markdown")
            
            if parsed_spec.parsing_errors:
                logger.warning(
                    f"Parsing completed with {len(parsed_spec.parsing_errors)} warnings"
                )
                errors.extend(parsed_spec.parsing_errors)
            
            logger.info(f"✓ Parsed {len(parsed_spec.test_cases)} test cases")
            
            # Step 3: Generate pytest code
            generated_tests = await self._prepare_generated_tests(
                parsed_spec,
                run_id,
            )
            
            pytest_code = await self._generate_code(
                generated_tests,
                config.target_server.base_url,
                project_dir=project_dir,
            )
            
            logger.info("✓ Generated pytest code")
            
            # Step 4: Execute tests
            summary = await self._run_pytest(pytest_code, run_id, config, project_dir=project_dir)
            
            logger.info(
                f"✓ Execution complete: {summary.passed} passed, "
                f"{summary.failed} failed, {summary.errors} errors"
            )
            
            # Step 5: Save results to database
            await self._save_results_to_db(
                project_id,
                generated_tests,
                summary,
                db,
            )
            
            logger.info("✓ Results saved to database")
            
            # Step 6: Update project status
            project.status = "COMPLETED"
            await db.commit()
            
            return {
                "success": True,
                "summary": summary.to_dict(),
                "errors": errors,
                "run_id": run_id,
            }
            
        except (MarkdownParseError, CodeGenerationError, PytestExecutionError) as e:
            logger.error(f"Execution failed: {e}")
            await self._update_project_status(project_id, "FAILED", db)
            return {
                "success": False,
                "summary": None,
                "errors": [str(e)] + errors,
                "run_id": run_id,
            }
        except Exception as e:
            logger.error(f"Unexpected error during execution: {e}", exc_info=True)
            await self._update_project_status(project_id, "FAILED", db)
            return {
                "success": False,
                "summary": None,
                "errors": [f"Unexpected error: {str(e)}"] + errors,
                "run_id": run_id,
            }
    
    # ========================================================================
    # PIPELINE STEPS
    # ========================================================================
    
    async def _parse_markdown(self, markdown_content: str) -> ParsedTestSpecification:
        """
        Step 1: Parse markdown into structured format.
        
        Raises:
            MarkdownParseError: If parsing fails critically
        """
        logger.debug("Parsing markdown specification...")
        
        try:
            spec = await asyncio.get_event_loop().run_in_executor(
                None,
                self.parser.parse,
                markdown_content,
            )
            return spec
        except Exception as e:
            raise MarkdownParseError(f"Failed to parse markdown: {str(e)}")
    
    async def _prepare_generated_tests(
        self,
        spec: ParsedTestSpecification,
        run_id: str,
    ) -> List[GeneratedTest]:
        """
        Step 2: Convert parsed tests to GeneratedTest objects.
        """
        logger.debug("Preparing test objects...")
        
        generated_tests = []
        for idx, parsed_test in enumerate(spec.test_cases):
            test_id = f"{run_id}_{idx}"
            generated = GeneratedTest.from_parsed(parsed_test, test_id)
            generated_tests.append(generated)
            
            logger.debug(f"Prepared test: {generated.function_name}")
        
        return generated_tests
    
    async def _generate_code(
        self,
        tests: List[GeneratedTest],
        base_url: str,
        project_dir: Path | None = None,
    ) -> str:
        """
        Step 3: Generate pytest code from GeneratedTest objects.
        
        Raises:
            CodeGenerationError: If code generation fails
        """
        logger.debug(f"Generating pytest code for {len(tests)} tests...")
        
        try:
            code = await asyncio.get_event_loop().run_in_executor(
                None,
                self.code_generator.generate_code,
                tests,
                base_url,
                10,
                project_dir,
            )
            return code
        except Exception as e:
            raise CodeGenerationError(f"Failed to generate code: {str(e)}")
    
    def _start_project_server(
        self,
        project_dir: Path,
        target_port: int,
    ) -> Tuple[subprocess.Popen, str, Path]:
        """
        Start the uploaded project's server as a subprocess.
        
        1. Detects the entry point (main.py, app.py, etc.)
        2. Launches it with uvicorn on the target port
        3. Waits up to 15 seconds for the server to be ready
        4. Returns the process handle, target URL, and actual project root
        
        Args:
            project_dir: Root directory of the uploaded project
            target_port: Port to run the server on
            
        Returns:
            Tuple of (server_process, target_url, actual_project_root)
            
        Raises:
            PytestExecutionError: If server fails to start or become ready
        """
        logger.info(f"Starting project server on port {target_port}...")
        
        # Detect entry point (also returns the normalized project directory)
        entry_point = _find_entry_point(project_dir)
        if not entry_point:
            raise PytestExecutionError(
                f"Could not find entry point in {project_dir} or subdirectories. "
                f"Searched for: main.py, app.py, run.py, server.py, asgi.py, wsgi.py"
            )
        
        module_name, app_var = entry_point
        target_url = f"http://127.0.0.1:{target_port}"
        
        # If the directory contains a single subdirectory only (common in zip extracts),
        # use that as the actual project root
        effective_dir = project_dir
        try:
            entries = list(project_dir.iterdir())
            dirs = [e for e in entries if e.is_dir() and not e.name.startswith('.')]
            files = [e for e in entries if e.is_file()]
            
            if len(dirs) == 1 and len(files) == 0:
                effective_dir = dirs[0]
        except Exception:
            pass
        
        # Start the server via uvicorn
        # Disable file watching/reload to prevent interference with test file writes
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            f"{module_name}:{app_var}",
            "--port",
            str(target_port),
            "--host",
            "127.0.0.1",
            "--no-reload",  # ← Disable file watching
        ]
        
        logger.debug(f"Launching: {' '.join(cmd)} (cwd={effective_dir})")
        
        try:
            # Use DEVNULL for stdout/stderr to avoid pipe buffer deadlock
            # We don't need to capture server output, only test output matters
            server_proc = subprocess.Popen(
                cmd,
                cwd=str(effective_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise PytestExecutionError(
                f"Failed to start server subprocess: {e}"
            ) from e
        
        # Wait for server to be ready (poll with retries, max 30 seconds)
        max_retries = 60  # 60 * 0.5s = 30 seconds (increased from 15s for slow systems)
        retry_count = 0
        
        logger.debug(f"Waiting for server to be ready at {target_url}...")
        
        while retry_count < max_retries:
            try:
                if httpx:
                    response = httpx.get(target_url, timeout=1.0)
                    # Even a 404/500 means the server is up and responding
                    logger.info(f"✓ Project server ready at {target_url}")
                    return server_proc, target_url, effective_dir
                else:
                    # Fallback: just try a TCP connection if httpx not available
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        result = s.connect_ex(("127.0.0.1", target_port))
                        if result == 0:
                            logger.info(f"✓ Project server ready at {target_url}")
                            return server_proc, target_url, effective_dir
            except Exception:
                # Not ready yet, keep trying
                pass
            
            time.sleep(0.5)
            retry_count += 1
        
        # Server failed to start within timeout
        try:
            server_proc.kill()
            server_proc.wait(timeout=2)
        except Exception:
            pass
        
        raise PytestExecutionError(
            f"Uploaded project server did not start within 30s on port {target_port}. "
            f"Entry point: {module_name}:{app_var}. "
            f"Check that the project has a valid uvicorn-compatible entry point "
            f"(FastAPI, Flask, or Starlette) and all dependencies are installed."
        )


    
    async def _run_pytest(
        self,
        pytest_code: str,
        run_id: str,
        config: ExecutionConfig,
        project_dir: Path | None = None,
    ) -> TestRunSummary:
        """
        Step 4: Execute pytest on generated code.
        
        This method handles the full server lifecycle:
        1. Start the uploaded project's server (if project_dir provided & entry point found)
        2. Generate pytest code with the correct target URL
        3. Execute pytest
        4. Teardown the server
        
        For non-server projects (no entry point found), falls back to direct pytest execution.
        
        Raises:
            PytestExecutionError: If execution fails
        """
        logger.debug("Executing pytest...")
        
        server_proc = None
        target_url = config.target_server.base_url
        actual_project_dir = project_dir
        
        try:
            # If we have an uploaded project, try to start its server automatically
            if project_dir and project_dir.exists():
                logger.info(f"Detected uploaded project at {project_dir}")
                
                try:
                    # Try to find and start the project server
                    server_port = find_free_port()
                    logger.debug(f"Allocated port {server_port} for project server")
                    
                    server_proc, target_url, actual_project_dir = self._start_project_server(
                        project_dir,
                        server_port,
                    )
                    logger.info(f"Server lifecycle started: {target_url}")
                    
                    # Give server time to fully stabilize before writing test files
                    await asyncio.sleep(0.5)
                    
                    # Regenerate pytest code with the correct target URL
                    logger.debug(f"Regenerating pytest code with target URL: {target_url}")
                    if "http://127.0.0.1:8000" in pytest_code or "http://localhost:8000" in pytest_code:
                        original_url = config.target_server.base_url
                        pytest_code = pytest_code.replace(
                            original_url,
                            target_url,
                        )
                        logger.debug(f"Updated pytest code URLs: {original_url} -> {target_url}")
                
                except PytestExecutionError as e:
                    # No entry point found — fall back to non-server testing
                    logger.warning(
                        f"Could not start server: {e}. "
                        f"Falling back to non-server pytest execution."
                    )
                    server_proc = None
                    target_url = config.target_server.base_url
                    # Do NOT modify pytest_code; use configured target URL
            else:
                logger.debug(
                    f"No project_dir provided or directory does not exist. "
                    f"Using configured target URL: {target_url}"
                )
            
            # Persist to disk for workflow/debug visibility.
            # Do this AFTER server is stable to avoid reload triggers.
            settings = get_settings()
            generated_dir = Path(settings.GENERATED_DIR)
            generated_dir.mkdir(parents=True, exist_ok=True)

            test_file = generated_dir / "test_generated.py"
            test_file.write_text(pytest_code, encoding="utf-8")

            # Also store per-run copy to avoid losing history.
            run_dir = generated_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "test_generated.py").write_text(pytest_code, encoding="utf-8")

            logger.debug(f"Test file persisted to: {test_file}")
            
            # Give file system time to settle before pytest scans
            await asyncio.sleep(0.2)

            try:
                summary = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.pytest_runner.run_tests,
                    test_file,
                    config.pytest_timeout_seconds,
                    config.pytest_verbose,
                    True,
                    actual_project_dir,
                )

                summary.project_id = ""  # Will be set by caller
                return summary

            except Exception as e:
                raise PytestExecutionError(f"Failed to execute pytest: {str(e)}") from e
        
        finally:
            # Teardown: Kill the server subprocess if it was started
            if server_proc is not None:
                logger.info("Tearing down project server...")
                try:
                    server_proc.kill()
                    # Wait with a short timeout for graceful shutdown
                    wait_result = server_proc.wait(timeout=2)
                    logger.info(f"✓ Project server terminated (exit code: {wait_result})")
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Server did not terminate gracefully, forcing kill..."
                    )
                    try:
                        server_proc.kill()
                        server_proc.wait(timeout=1)
                    except Exception as e:
                        logger.warning(f"Error during forced kill: {e}")
                except Exception as e:
                    logger.warning(f"Error during server teardown: {e}")




    
    async def _save_results_to_db(
        self,
        project_id: str,
        generated_tests: List[GeneratedTest],
        summary: TestRunSummary,
        db: AsyncSession,
    ) -> None:
        """
        Step 5: Persist results to database.
        """
        logger.debug("Saving results to database...")
        
        # Create TestRun record
        test_run = TestRun(
            project_id=project_id,
            status=summary.status,
            total_tests=summary.total,
            passed=summary.passed,
            failed=summary.failed,
            errors=summary.errors,
            duration_seconds=summary.duration_seconds,
        )
        db.add(test_run)
        await db.flush()
        
        # Create TestResult records
        for result in summary.results:
            # Create or get TestCase
            test_case = await self._get_or_create_test_case(
                project_id,
                result,
                db,
            )
            
            # Create TestResult
            test_result = TestResult(
                test_case_id=test_case.id,
                test_run_id=test_run.id,
                status=result.outcome.value,
                error_message=(
                    result.failure.assertion_message
                    if result.failure else None
                ),
                duration_seconds=result.metrics.duration_ms / 1000.0,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            db.add(test_result)
        
        await db.commit()
        logger.debug("Results saved successfully")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _get_project(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> Optional[Project]:
        """Retrieve project from database."""
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_or_create_test_case(
        self,
        project_id: str,
        result: IndividualTestResult,
        db: AsyncSession,
    ) -> TestCase:
        """Get or create a test case for the result."""
        # Try to find existing test case
        query = select(TestCase).where(
            (TestCase.project_id == project_id) &
            (TestCase.target_function == result.test_name)
        )
        existing = await db.execute(query)
        test_case = existing.scalar_one_or_none()
        
        if test_case:
            return test_case
        
        # Create new test case
        test_case = TestCase(
            project_id=project_id,
            target_file="generated",
            target_function=result.test_name,
            test_type="integration",
            test_code=f"# Generated test: {result.test_name}",
            status="GENERATED",
        )
        db.add(test_case)
        await db.flush()
        
        return test_case
    
    async def _update_project_status(
        self,
        project_id: str,
        status: str,
        db: AsyncSession,
    ) -> None:
        """Update project status in database."""
        try:
            project = await self._get_project(project_id, db)
            if project:
                project.status = status
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update project status: {e}")
    
    @staticmethod
    async def get_event_loop():
        """Helper to get event loop."""
        import asyncio
        return asyncio.get_event_loop()


# ============================================================================
# Entry Point Function (for background tasks)
# ============================================================================

async def run_markdown_execution_v2(
    project_id: str,
    markdown_content: str,
    db: AsyncSession,
    config: Optional[ExecutionConfig] = None,
) -> Dict[str, Any]:
    """
    Execute markdown tests with the improved engine.
    
    This is the async entry point for background task execution.
    
    Args:
        project_id: Project ID
        markdown_content: Markdown test specification
        db: Database session
        config: Optional execution configuration
        
    Returns:
        Execution result dictionary
    """
    engine = ImprovedTestExecutionEngine(config)
    return await engine.execute_markdown_tests(
        project_id,
        markdown_content,
        db,
        config,
    )


# Import asyncio at the top level (needed for executor)
import asyncio
