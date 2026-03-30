"""
AI Test Platform — Test Generation & Execution Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.base import async_session_factory

from models.base import get_db
from models.project import Project
from models.test_case import TestCase
from schemas.test_case import TestCaseResponse, TestGenerateRequest
from schemas.result import ExecutionRequest
from utils.logger import get_logger

router = APIRouter(prefix="/tests", tags=["Tests"])
logger = get_logger(__name__)


@router.post(
    "/generate/{project_id}",
    status_code=202,
    summary="Generate tests for a project",
    description="Trigger AI-powered test generation for a parsed project.",
)
async def generate_tests(
    project_id: str,
    request: TestGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger test generation for a project.
    The project must be in PARSED status.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status not in ("PARSED", "GENERATED", "COMPLETED"):
        raise HTTPException(
            status_code=400,
            detail=f"Project must be parsed before generating tests. Current status: {project.status}",
        )

    # Update status
    project.status = "GENERATING"
    await db.flush()

    # TODO: Enqueue generation task via Celery
    # generation_task.delay(project_id, request.model_dump() if request else {})

    logger.info("Test generation triggered", project_id=project_id)

    return {
        "project_id": project_id,
        "status": "GENERATING",
        "message": "Test generation has been queued.",
    }


@router.get(
    "/{project_id}",
    response_model=list[TestCaseResponse],
    summary="List generated test cases",
)
async def list_test_cases(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all generated test cases for a project."""
    result = await db.execute(
        select(TestCase)
        .where(TestCase.project_id == project_id)
        .order_by(TestCase.created_at.desc())
    )
    test_cases = result.scalars().all()
    return [TestCaseResponse.model_validate(tc) for tc in test_cases]


@router.post(
    "/execute/{project_id}",
    status_code=202,
    summary="Execute tests for a project",
    description="Run generated tests in a sandboxed environment.",
)
async def execute_tests(
    project_id: str,
    background_tasks: BackgroundTasks,
    request: ExecutionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute generated tests for a project.
    Runs pytest in a sandboxed environment.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status not in ("PARSED", "GENERATED", "COMPLETED", "FAILED"):
        raise HTTPException(
            status_code=400,
            detail=f"Tests must be generated before execution. Current status: {project.status}",
        )

    if not request or not request.markdown_content:
        raise HTTPException(status_code=400, detail="Missing markdown_content in request body.")

    # We need a new isolated db session for the background task
    async def bg_execution(pid, md, base_url):
        # Use the improved v2 engine which adapts tests to project type
        from core.executor.execution_engine_v2 import run_markdown_execution_v2
        async with async_session_factory() as session:
            # base_url is only used for API-type projects; module projects ignore it safely
            await run_markdown_execution_v2(pid, md, session, config=None)

    # Commit status update now so the SQLite write lock is released
    # before the background task opens its own session
    project.status = "EXECUTING"
    await db.commit()

    # Use provided base URL or fall back to config
    target_url = request.target_base_url if request and request.target_base_url else None
    background_tasks.add_task(bg_execution, project_id, request.markdown_content, target_url)

    logger.info("Test execution triggered in background", project_id=project_id)

    return {
        "project_id": project_id,
        "status": "EXECUTING",
        "message": "Test execution has been queued.",
    }
