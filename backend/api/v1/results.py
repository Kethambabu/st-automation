"""
AI Test Platform — Test Results Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.base import get_db
from models.test_result import TestRun
from schemas.result import TestRunResponse

router = APIRouter(prefix="/results", tags=["Results"])


@router.get(
    "/{project_id}",
    response_model=list[TestRunResponse],
    summary="Get test results for a project",
)
async def get_results(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all test run results for a project."""
    result = await db.execute(
        select(TestRun)
        .where(TestRun.project_id == project_id)
        .options(selectinload(TestRun.results))
        .order_by(TestRun.executed_at.desc())
    )
    runs = result.scalars().all()

    if not runs:
        raise HTTPException(status_code=404, detail="No test runs found for this project.")

    return [TestRunResponse.model_validate(run) for run in runs]


@router.get(
    "/run/{run_id}",
    response_model=TestRunResponse,
    summary="Get a specific test run",
)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a specific test run with all individual results."""
    result = await db.execute(
        select(TestRun)
        .where(TestRun.id == run_id)
        .options(selectinload(TestRun.results))
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Test run not found.")

    return TestRunResponse.model_validate(run)
