"""
AI Test Platform — File Handling Utilities
"""

import os
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_project_id() -> str:
    """Generate a unique project identifier."""
    return str(uuid4())


def save_upload(file_content: bytes, filename: str, project_id: str) -> Path:
    """
    Save an uploaded file to the uploads directory.
    Returns the path to the saved file.
    """
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR) / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / filename
    file_path.write_bytes(file_content)
    logger.info("File saved", filename=filename, project_id=project_id, size=len(file_content))
    return file_path


def extract_zip(zip_path: Path, project_id: str) -> Path:
    """
    Safely extract a ZIP file to the extraction directory.
    Returns the path to the extracted directory.
    Protects against zip-slip (path traversal) attacks.
    """
    settings = get_settings()
    extract_dir = Path(settings.EXTRACT_DIR) / project_id
    extract_dir.mkdir(parents=True, exist_ok=True)

    extract_dir_abs = os.path.abspath(str(extract_dir))
    
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.namelist():
            # Security: Prevent path traversal attacks using fast string normalization
            member_path_abs = os.path.abspath(str(extract_dir / member))
            if not member_path_abs.startswith(extract_dir_abs):
                raise ValueError(f"Zip slip detected: {member}")
        zip_ref.extractall(extract_dir)

    logger.info("ZIP extracted", project_id=project_id, path=str(extract_dir))
    return extract_dir


def scan_source_files(
    directory: Path,
    extensions: set[str] | None = None,
) -> list[Path]:
    """
    Recursively discover source files in a directory.
    Filters by file extensions if provided.
    """
    if extensions is None:
        extensions = {".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"}

    source_files = []
    for root, dirs, files in os.walk(directory):
        # Skip common non-source directories
        dirs[:] = [
            d for d in dirs
            if d not in {"node_modules", ".git", "__pycache__", "venv", ".venv", "env", ".tox"}
        ]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix in extensions:
                source_files.append(fpath)

    logger.info("Source files scanned", directory=str(directory), count=len(source_files))
    return source_files


def cleanup_project(project_id: str) -> None:
    """Remove all storage artifacts for a project."""
    settings = get_settings()
    for dir_name in [settings.UPLOAD_DIR, settings.EXTRACT_DIR, settings.GENERATED_DIR]:
        project_dir = Path(dir_name) / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)
    logger.info("Project cleaned up", project_id=project_id)
