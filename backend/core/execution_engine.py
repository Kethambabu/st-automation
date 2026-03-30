"""
AI Test Platform — Background Execution Engine
"""
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.project import Project
from models.test_case import TestCase
from models.test_result import TestRun, TestResult
from core.executor.markdown_runner import MarkdownTestRunner
from core.executor.test_config import get_test_config

logger = logging.getLogger(__name__)

import asyncio

async def run_markdown_execution(
    project_id: str,
    markdown_content: str,
    db: AsyncSession,
    target_base_url: str | None = None,
):
    """
    Execute markdown test specs and save results.
    """
    try:
        # Check project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            logger.error(f"Project {project_id} not found for execution")
            return

        # Execute tests via MarkdownRunner in a threadpool so it doesn't stall the event loop or DB locks
        config = get_test_config()
        # Use provided base URL or fall back to config
        base_url = target_base_url if target_base_url else config.target_base_url
        logger.info(f"Test execution config: base_url={base_url}")
        runner = MarkdownTestRunner(target_base_url=base_url)
        output = await asyncio.to_thread(runner.run_markdown, markdown_content)
        logger.info(f"Test execution completed: {len(output.get('passed', []))} passed, {len(output.get('failed', []))} failed")
        
        passed_tests = output.get("passed", [])
        failed_tests = output.get("failed", [])
        
        total = len(passed_tests) + len(failed_tests)
        passed_count = len(passed_tests)
        failed_count = len(failed_tests)
        
        # Create TestRun record
        test_run = TestRun(
            project_id=project_id,
            status="FAILED" if failed_count > 0 else "PASSED",
            total_tests=total,
            passed=passed_count,
            failed=failed_count,
            errors=0,
            coverage_percent=0.0
        )
        db.add(test_run)
        await db.flush()
        
        # Helper to get or create TestCase based on name
        async def get_or_create_test_case(name: str):
            res = await db.execute(select(TestCase).where(TestCase.project_id == project_id, TestCase.target_function == name))
            tc = res.scalars().first()
            if not tc:
                tc = TestCase(
                    project_id=project_id,
                    target_file="",
                    target_function=name,
                    test_type="functional",
                    test_code=""
                )
                db.add(tc)
                await db.flush()
            return tc
            
        # Save TestResults
        for p_name in passed_tests:
            tc = await get_or_create_test_case(p_name)
            tr = TestResult(
                test_case_id=tc.id,
                test_run_id=test_run.id,
                status="PASSED"
            )
            db.add(tr)
            
        for f_data in failed_tests:
            f_name = f_data["name"]
            f_error = f_data["error"]
            tc = await get_or_create_test_case(f_name)
            tr = TestResult(
                test_case_id=tc.id,
                test_run_id=test_run.id,
                status="FAILED",
                error_message=f_error
            )
            db.add(tr)
            
        project.status = "COMPLETED"
        await db.commit()
        logger.info(f"Execution completed for project {project_id}.")
        
    except Exception as e:
        logger.error(f"Execution failed for project {project_id}: {e}", exc_info=True)
        await db.rollback()
        try:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if project:
                project.status = "FAILED"
                await db.commit()
        except Exception:
            pass
