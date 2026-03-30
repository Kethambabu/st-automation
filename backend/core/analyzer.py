"""
AI Test Platform — Project Analyzer (Core Orchestrator)

Top-level module that orchestrates the full analysis pipeline:

    Upload → Extract → Scan → Parse (AST) → Detect APIs → Structured JSON

Usage:
    analyzer = ProjectAnalyzer()

    # From a ZIP file:
    result = analyzer.analyze_zip(zip_path, project_name="my-app")

    # From an already-extracted directory:
    result = analyzer.analyze_directory(Path("./my-project"), project_name="my-app")

    # Get JSON output:
    print(result.model_dump_json(indent=2))
"""

from pathlib import Path

from core.parser.ast_parser import PythonASTParser, ParsedModule
from core.parser.api_detector import APIRouteDetector
from core.parser.code_models import (
    ProjectAnalysis,
    ModuleInfo,
    ClassInfo,
    FunctionInfo,
    APIInfo,
)
from utils.file_utils import extract_zip, scan_source_files, generate_project_id
from utils.logger import get_logger

logger = get_logger(__name__)


class ProjectAnalyzer:
    """
    Orchestrates the full code analysis pipeline.

    Coordinates:
      1. Project extraction (ZIP → files)
      2. Source file scanning (recursive discovery)
      3. AST parsing (functions, classes, imports)
      4. API route detection (FastAPI/Flask routes)
      5. Structured output generation (JSON)

    Designed to be extensible — add new parsers for Java, Node.js, etc.
    by creating language-specific parser classes and registering them here.
    """

    def __init__(self):
        self._ast_parser = PythonASTParser()
        self._api_detector = APIRouteDetector()

        # ── Language → Extensions mapping (extensible) ──
        self._language_extensions: dict[str, set[str]] = {
            "python": {".py"},
            # Future: "java": {".java"}, "javascript": {".js", ".mjs"}, etc.
        }

    def analyze_zip(
        self,
        zip_path: Path,
        project_name: str,
        project_id: str | None = None,
    ) -> ProjectAnalysis:
        """
        Full pipeline: extract a ZIP and analyze the project inside.

        Args:
            zip_path: Path to the uploaded ZIP file
            project_name: Human-readable project name
            project_id: Optional project ID (auto-generated if not provided)

        Returns:
            ProjectAnalysis with all modules, classes, functions, and APIs
        """
        pid = project_id or generate_project_id()
        logger.info("Starting ZIP analysis", project_name=project_name, project_id=pid)

        # Step 1: Extract
        extract_dir = extract_zip(zip_path, pid)

        # Step 2-5: Analyze the extracted directory
        return self.analyze_directory(extract_dir, project_name, pid)

    def analyze_directory(
        self,
        directory: Path,
        project_name: str,
        project_id: str | None = None,
    ) -> ProjectAnalysis:
        """
        Analyze an already-extracted project directory.

        Args:
            directory: Root directory of the project
            project_name: Human-readable project name
            project_id: Optional project ID

        Returns:
            ProjectAnalysis with all modules, classes, functions, and APIs
        """
        pid = project_id or generate_project_id()
        logger.info(
            "Analyzing project directory",
            directory=str(directory),
            project_name=project_name,
        )

        # Step 2: Scan for source files
        python_files = scan_source_files(directory, extensions={".py"})

        if not python_files:
            logger.warning("No Python files found", directory=str(directory))
            return ProjectAnalysis(
                project_name=project_name,
                project_id=pid,
                language="python",
            )

        # Step 3 & 4: Parse each file and detect APIs
        all_modules: list[ModuleInfo] = []
        all_classes: list[ClassInfo] = []
        all_functions: list[FunctionInfo] = []
        all_apis: list[APIInfo] = []
        total_lines = 0

        for file_path in python_files:
            # Make path relative for cleaner output
            try:
                rel_path = str(file_path.relative_to(directory))
            except ValueError:
                rel_path = str(file_path)

            # ── AST Parsing ────────────────────────────
            parsed = self._ast_parser.parse_file(file_path)
            if parsed is None:
                continue

            total_lines += parsed.total_lines

            # Build module info
            module_name = self._path_to_module_name(rel_path)
            module_info = ModuleInfo(
                file_path=rel_path,
                module_name=module_name,
                imports=parsed.imports,
                global_variables=parsed.global_variables,
                function_count=len(parsed.functions),
                class_count=len(parsed.classes),
                total_lines=parsed.total_lines,
            )
            all_modules.append(module_info)

            # Extract top-level functions
            for func in parsed.functions:
                all_functions.append(FunctionInfo(
                    name=func.name,
                    file_path=rel_path,
                    args=func.args,
                    return_type=func.return_annotation,
                    docstring=func.docstring,
                    decorators=func.decorators,
                    line_start=func.line_start,
                    line_end=func.line_end,
                    is_method=False,
                    is_async=func.is_async,
                    complexity=func.complexity,
                ))

            # Extract classes and their methods
            for cls in parsed.classes:
                methods = []
                for method in cls.methods:
                    method_info = FunctionInfo(
                        name=method.name,
                        file_path=rel_path,
                        args=method.args,
                        return_type=method.return_annotation,
                        docstring=method.docstring,
                        decorators=method.decorators,
                        line_start=method.line_start,
                        line_end=method.line_end,
                        is_method=True,
                        is_async=method.is_async,
                        complexity=method.complexity,
                        parent_class=cls.name,
                    )
                    methods.append(method_info)
                    all_functions.append(method_info)

                all_classes.append(ClassInfo(
                    name=cls.name,
                    file_path=rel_path,
                    bases=cls.bases,
                    docstring=cls.docstring,
                    decorators=cls.decorators,
                    methods=methods,
                    method_count=len(methods),
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                ))

            # ── API Detection ──────────────────────────
            detected_apis = self._api_detector.detect_from_file(file_path)
            for api in detected_apis:
                all_apis.append(APIInfo(
                    path=api.path,
                    http_method=api.http_method.upper(),
                    function_name=api.function_name,
                    framework=api.framework,
                    file_path=rel_path,
                    line_number=api.line_number,
                    args=api.args,
                    docstring=api.docstring,
                    response_model=api.response_model,
                ))

        # Step 5: Build the final structured output
        analysis = ProjectAnalysis(
            project_name=project_name,
            project_id=pid,
            language="python",
            total_files=len(python_files),
            total_lines=total_lines,
            modules=all_modules,
            classes=all_classes,
            functions=all_functions,
            apis=all_apis,
            total_modules=len(all_modules),
            total_classes=len(all_classes),
            total_functions=len(all_functions),
            total_apis=len(all_apis),
        )

        logger.info(
            "Project analysis complete",
            project_name=project_name,
            files=analysis.total_files,
            modules=analysis.total_modules,
            classes=analysis.total_classes,
            functions=analysis.total_functions,
            apis=analysis.total_apis,
            lines=analysis.total_lines,
        )

        return analysis

    def _path_to_module_name(self, rel_path: str) -> str:
        """Convert a relative file path to a Python module name."""
        # "core/parser/ast_parser.py" → "core.parser.ast_parser"
        module = rel_path.replace("\\", "/").replace("/", ".")
        if module.endswith(".py"):
            module = module[:-3]
        if module.endswith(".__init__"):
            module = module[:-9]
        return module
