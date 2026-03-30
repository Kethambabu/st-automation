"""
AI Test Platform — File Upload API Endpoints

Handles:
  - ZIP file uploads
  - GitHub repository URL submissions
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.project import Project
from schemas.project import UploadResponse, ProjectCreate
from utils.file_utils import generate_project_id, save_upload, extract_zip
from utils.logger import get_logger
from config import get_settings

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = get_logger(__name__)
settings = get_settings()


@router.post(
    "/zip",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload a ZIP file",
    description="Upload a project as a ZIP archive for test generation.",
)
async def upload_zip(
    file: UploadFile = File(..., description="ZIP file to upload"),
    project_name: str = Form(..., description="Name for the project"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a ZIP file containing a project's source code.

    - Validates file type and size
    - Saves to storage
    - Creates a project record
    - Returns project_id for tracking
    """
    # ── Validate file type ─────────────────────────────
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip files are accepted.",
        )

    # ── Validate file size ─────────────────────────────
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    import asyncio
    # ── Save & create project ──────────────────────────
    project_id = generate_project_id()
    try:
        saved_path = await asyncio.to_thread(save_upload, content, file.filename, project_id)
        extract_dir = await asyncio.to_thread(extract_zip, saved_path, project_id)

        project = Project(
            id=project_id,
            name=project_name,
            source_type="ZIP",
            status="UPLOADED",
            storage_path=str(extract_dir),
        )
        db.add(project)
        await db.flush()

        logger.info(
            "Project created from ZIP upload",
            project_id=project_id,
            filename=file.filename,
            size_bytes=len(content),
        )

        return UploadResponse(
            project_id=project_id,
            name=project_name,
            status="UPLOADED",
            message="File uploaded successfully. Ingestion will begin shortly.",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Upload failed", error=str(e), project_id=project_id)
        raise HTTPException(status_code=500, detail="Upload processing failed.")


@router.post(
    "/github",
    response_model=UploadResponse,
    status_code=202,
    summary="Submit a GitHub repository URL",
    description="Submit a GitHub repository URL for cloning and test generation.",
)
async def upload_github(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a GitHub repository URL for cloning.

    - Validates the URL format
    - Creates a project record
    - Triggers async cloning
    """
    # ── Basic URL validation ───────────────────────────
    if not payload.github_url.startswith(("https://github.com/", "git@github.com:")):
        raise HTTPException(
            status_code=400,
            detail="Only GitHub repository URLs are supported.",
        )

    project_id = generate_project_id()

    project = Project(
        id=project_id,
        name=payload.name,
        source_type="GITHUB",
        source_url=payload.github_url,
        status="UPLOADED",
    )
    db.add(project)
    await db.flush()

    logger.info(
        "Project created from GitHub URL",
        project_id=project_id,
        url=payload.github_url,
    )

    return UploadResponse(
        project_id=project_id,
        name=payload.name,
        status="UPLOADED",
        message="GitHub repository submitted. Cloning will begin shortly.",
    )
