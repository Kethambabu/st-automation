"""
AI Test Platform — Structured Code Models

Pydantic models representing the complete analysis output of a project.
These models define the JSON schema for the structured project representation.

Example output:
{
    "project_name": "my-app",
    "language": "python",
    "total_files": 12,
    "modules": [...],
    "classes": [...],
    "functions": [...],
    "apis": []
}
"""

from pydantic import BaseModel, Field


class FunctionInfo(BaseModel):
    """Structured representation of a function/method."""
    name: str
    file_path: str
    args: list[str] = []
    return_type: str | None = None
    docstring: str | None = None
    decorators: list[str] = []
    line_start: int = 0
    line_end: int = 0
    is_method: bool = False
    is_async: bool = False
    complexity: int = 1
    parent_class: str | None = None


class ClassInfo(BaseModel):
    """Structured representation of a class."""
    name: str
    file_path: str
    bases: list[str] = []
    docstring: str | None = None
    decorators: list[str] = []
    methods: list[FunctionInfo] = []
    method_count: int = 0
    line_start: int = 0
    line_end: int = 0


class ModuleInfo(BaseModel):
    """Structured representation of a Python module (file)."""
    file_path: str
    module_name: str
    imports: list[str] = []
    global_variables: list[str] = []
    function_count: int = 0
    class_count: int = 0
    total_lines: int = 0


class APIInfo(BaseModel):
    """Structured representation of a detected API route."""
    path: str
    http_method: str
    function_name: str
    framework: str
    file_path: str
    line_number: int
    args: list[str] = []
    docstring: str | None = None
    response_model: str | None = None


class ProjectAnalysis(BaseModel):
    """
    Complete structured analysis of a software project.

    This is the top-level output schema containing all extracted
    modules, classes, functions, and API routes.
    """
    project_name: str
    project_id: str | None = None
    language: str = "python"
    total_files: int = 0
    total_lines: int = 0

    modules: list[ModuleInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    apis: list[APIInfo] = Field(default_factory=list)

    # Summary statistics
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_apis: int = 0
