"""
AI Test Platform — Project Analysis API Endpoints

Provides endpoints to:
  - Trigger full project analysis (POST)
  - Retrieve analysis results as structured JSON (GET)
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.project import Project
from core.analyzer import ProjectAnalyzer
from core.parser.code_models import ProjectAnalysis
from schemas.analysis import AnalysisSummary
from utils.logger import get_logger

router = APIRouter(prefix="/analysis", tags=["Analysis"])
logger = get_logger(__name__)

# Shared analyzer instance
_analyzer = ProjectAnalyzer()


@router.post(
    "/{project_id}",
    response_model=AnalysisSummary,
    summary="Analyze a project",
    description="Run full structural analysis on an uploaded project: parse code, detect APIs, extract classes and functions.",
)
async def analyze_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger structural analysis for an uploaded project.

    The project must be in UPLOADED status (already extracted).
    Parses all Python files, detects classes/functions/APIs, and
    updates the project status to PARSED.
    """
    # Fetch project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.storage_path:
        raise HTTPException(
            status_code=400,
            detail="Project has no extracted files. Upload a ZIP first.",
        )

    extract_dir = Path(project.storage_path)
    if not extract_dir.exists():
        raise HTTPException(
            status_code=400,
            detail="Project files not found on disk. Re-upload required.",
        )

    # Update status
    project.status = "PARSING"
    await db.flush()

    import asyncio
    try:
        # Run the full analysis pipeline on a background thread so the server doesn't freeze
        analysis = await asyncio.to_thread(
            _analyzer.analyze_directory,
            directory=extract_dir,
            project_name=project.name,
            project_id=project_id,
        )

        # Update project record
        project.status = "PARSED"
        project.file_count = analysis.total_files
        project.language = analysis.language
        await db.flush()

        logger.info(
            "Project analysis completed",
            project_id=project_id,
            files=analysis.total_files,
            classes=analysis.total_classes,
            functions=analysis.total_functions,
            apis=analysis.total_apis,
        )

        return AnalysisSummary(
            project_id=project_id,
            project_name=project.name,
            status="PARSED",
            total_files=analysis.total_files,
            total_modules=analysis.total_modules,
            total_classes=analysis.total_classes,
            total_functions=analysis.total_functions,
            total_apis=analysis.total_apis,
            total_lines=analysis.total_lines,
            message="Analysis complete. Use GET /analysis/{project_id}/full for detailed JSON.",
        )

    except Exception as e:
        project.status = "FAILED"
        project.error_message = str(e)
        await db.flush()
        logger.error("Analysis failed", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get(
    "/{project_id}/full",
    response_model=ProjectAnalysis,
    summary="Get full analysis JSON",
    description="Retrieve the complete structured analysis with all modules, classes, functions, and APIs.",
)
async def get_full_analysis(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the full structured JSON analysis for a project.

    Re-runs the parser on the extracted files and returns
    the complete ProjectAnalysis object.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.storage_path:
        raise HTTPException(status_code=400, detail="No extracted files found.")

    extract_dir = Path(project.storage_path)
    if not extract_dir.exists():
        raise HTTPException(status_code=400, detail="Project files not found on disk.")

    # Run analysis and return full structured JSON
    import asyncio
    analysis = await asyncio.to_thread(
        _analyzer.analyze_directory,
        directory=extract_dir,
        project_name=project.name,
        project_id=project_id,
    )

    return analysis
