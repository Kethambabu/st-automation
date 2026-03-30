"""
AI Test Platform — API Route Detector

Detects web framework routes from Python source code using AST analysis.
Supports:
  - FastAPI routes (@app.get, @router.post, etc.)
  - Flask routes (@app.route, @blueprint.route, etc.)

Extensible architecture: add new detectors for Express.js, Spring Boot, etc.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Known HTTP methods ────────────────────────────────────
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# ── Known FastAPI/Flask variable names ────────────────────
FASTAPI_IDENTIFIERS = {"app", "router", "api_router", "api"}
FLASK_IDENTIFIERS = {"app", "blueprint", "bp", "api"}
FLASK_ROUTE_METHODS = {"route", "add_url_rule"}


@dataclass
class DetectedAPI:
    """Represents a detected API route."""
    path: str
    http_method: str
    function_name: str
    framework: str  # "fastapi" | "flask" | "unknown"
    file_path: str
    line_number: int
    args: list[str] = field(default_factory=list)
    docstring: str | None = None
    response_model: str | None = None
    decorators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "http_method": self.http_method.upper(),
            "function_name": self.function_name,
            "framework": self.framework,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "args": self.args,
            "docstring": self.docstring,
            "response_model": self.response_model,
            "decorators": self.decorators,
        }


class APIRouteDetector:
    """
    Detects API routes in Python source code via AST inspection.

    Identifies decorator patterns for FastAPI and Flask frameworks
    and extracts route metadata (path, HTTP method, function name).
    """

    def detect_from_file(self, file_path: Path) -> list[DetectedAPI]:
        """Detect API routes from a Python file."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.detect_from_source(source, str(file_path))
        except SyntaxError as e:
            logger.warning("Syntax error in file", file=str(file_path), error=str(e))
            return []
        except Exception as e:
            logger.error("Failed to detect APIs", file=str(file_path), error=str(e))
            return []

    def detect_from_source(self, source: str, file_path: str = "<string>") -> list[DetectedAPI]:
        """Detect API routes from Python source code string."""
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return []

        apis: list[DetectedAPI] = []
        framework = self._detect_framework(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    apis.extend(self._analyze_decorator(decorator, node, file_path, framework))

        if apis:
            logger.info(
                "API routes detected",
                file=file_path,
                count=len(apis),
                framework=framework,
            )
        return apis

    def _detect_framework(self, tree: ast.Module) -> str:
        """Detect which web framework is used based on imports."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "fastapi" in module.lower():
                    return "fastapi"
                if "flask" in module.lower():
                    return "flask"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.lower()
                    if "fastapi" in name:
                        return "fastapi"
                    if "flask" in name:
                        return "flask"
        return "unknown"

    def _analyze_decorator(
        self,
        decorator: ast.expr,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        framework: str,
    ) -> list[DetectedAPI]:
        """Analyze a decorator to see if it defines an API route."""

        # ── Pattern 1: @app.get("/path") or @router.post("/path") ──
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            attr_name = decorator.func.attr  # "get", "post", "route", etc.

            # FastAPI style: @app.get("/users")
            if attr_name in HTTP_METHODS:
                path = self._extract_path(decorator)
                if path:
                    return [self._build_api(
                        path=path,
                        http_method=attr_name,
                        func_node=func_node,
                        decorator=decorator,
                        file_path=file_path,
                        framework=framework if framework != "unknown" else "fastapi",
                    )]

            # Flask style: @app.route("/users", methods=["GET", "POST"])
            if attr_name in FLASK_ROUTE_METHODS:
                path = self._extract_path(decorator)
                methods = self._extract_flask_methods(decorator)
                if path:
                    return [
                        self._build_api(
                            path=path,
                            http_method=method.lower(),
                            func_node=func_node,
                            decorator=decorator,
                            file_path=file_path,
                            framework="flask",
                        )
                        for method in methods
                    ]

        # ── Pattern 2: @app.get (no parentheses, rare) ──
        if isinstance(decorator, ast.Attribute):
            if decorator.attr in HTTP_METHODS:
                return [self._build_api(
                    path="<unknown>",
                    http_method=decorator.attr,
                    func_node=func_node,
                    decorator=decorator,
                    file_path=file_path,
                    framework=framework,
                )]

        return []

    def _build_api(
        self,
        path: str,
        http_method: str,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        decorator: ast.expr,
        file_path: str,
        framework: str,
    ) -> DetectedAPI:
        """Build a DetectedAPI instance from parsed components."""
        # Extract function arguments (skip self/cls)
        args = [
            arg.arg for arg in func_node.args.args
            if arg.arg not in ("self", "cls")
        ]

        # Extract response_model if present (FastAPI)
        response_model = None
        if isinstance(decorator, ast.Call):
            for kw in decorator.keywords:
                if kw.arg == "response_model":
                    response_model = ast.unparse(kw.value)
                    break

        # Extract all decorators as strings
        all_decorators = [ast.unparse(d) for d in func_node.decorator_list]

        return DetectedAPI(
            path=path,
            http_method=http_method,
            function_name=func_node.name,
            framework=framework,
            file_path=file_path,
            line_number=func_node.lineno,
            args=args,
            docstring=ast.get_docstring(func_node),
            response_model=response_model,
            decorators=all_decorators,
        )

    def _extract_path(self, call_node: ast.Call) -> str | None:
        """Extract the URL path from a decorator call's first argument."""
        if call_node.args:
            first_arg = call_node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value
        # Also check for path= keyword
        for kw in call_node.keywords:
            if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
        return None

    def _extract_flask_methods(self, call_node: ast.Call) -> list[str]:
        """Extract HTTP methods from a Flask @app.route(methods=[...]) decorator."""
        for kw in call_node.keywords:
            if kw.arg == "methods" and isinstance(kw.value, ast.List):
                methods = []
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        methods.append(elt.value)
                return methods
        return ["GET"]  # Flask default

    def _get_name(self, node: ast.expr) -> str:
        """Extract a human-readable name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "<unknown>"
