"""
AI Test Platform — Project Schemas
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a project via GitHub URL."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    github_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to clone")


class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    id: str
    name: str
    source_type: str
    source_url: str | None = None
    status: str
    language: str | None = None
    file_count: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for listing projects."""
    projects: list[ProjectResponse]
    total: int


class UploadResponse(BaseModel):
    """Schema for file upload response."""
    project_id: str
    name: str
    status: str
    message: str
