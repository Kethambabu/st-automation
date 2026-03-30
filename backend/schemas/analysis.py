"""
AI Test Platform — Analysis Schemas
"""

from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    """Quick summary of analysis results."""
    project_id: str
    project_name: str
    status: str
    total_files: int = 0
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_apis: int = 0
    total_lines: int = 0
    message: str = ""
