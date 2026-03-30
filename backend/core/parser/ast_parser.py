"""
AI Test Platform — Python AST Parser

Parses Python source files using the built-in `ast` module to extract
structured code information: classes, functions, signatures, docstrings,
imports, and complexity metrics.
"""

import ast
from pathlib import Path
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedFunction:
    """Represents a parsed function or method."""
    name: str
    args: list[str]
    return_annotation: str | None = None
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    is_method: bool = False
    is_async: bool = False
    complexity: int = 1  # Cyclomatic complexity estimate

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "args": self.args,
            "return_annotation": self.return_annotation,
            "docstring": self.docstring,
            "decorators": self.decorators,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "is_method": self.is_method,
            "is_async": self.is_async,
            "complexity": self.complexity,
        }


@dataclass
class ParsedClass:
    """Represents a parsed class."""
    name: str
    bases: list[str]
    docstring: str | None = None
    methods: list[ParsedFunction] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bases": self.bases,
            "docstring": self.docstring,
            "methods": [m.to_dict() for m in self.methods],
            "decorators": self.decorators,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


@dataclass
class ParsedModule:
    """Represents a fully parsed Python module."""
    file_path: str
    imports: list[str] = field(default_factory=list)
    functions: list[ParsedFunction] = field(default_factory=list)
    classes: list[ParsedClass] = field(default_factory=list)
    global_variables: list[str] = field(default_factory=list)
    total_lines: int = 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "imports": self.imports,
            "functions": [f.to_dict() for f in self.functions],
            "classes": [c.to_dict() for c in self.classes],
            "global_variables": self.global_variables,
            "total_lines": self.total_lines,
        }


class PythonASTParser:
    """
    Parses Python source code using the AST module.

    Extracts structured metadata including functions, classes,
    imports, docstrings, and complexity estimates.
    """

    def parse_file(self, file_path: Path) -> ParsedModule | None:
        """Parse a single Python file and return structured data."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
            return self._analyze_module(tree, str(file_path), source)
        except SyntaxError as e:
            logger.warning("Syntax error in file", file=str(file_path), error=str(e))
            return None
        except Exception as e:
            logger.error("Failed to parse file", file=str(file_path), error=str(e))
            return None

    def parse_source(self, source: str, filename: str = "<string>") -> ParsedModule | None:
        """Parse Python source code string."""
        try:
            tree = ast.parse(source, filename=filename)
            return self._analyze_module(tree, filename, source)
        except SyntaxError as e:
            logger.warning("Syntax error in source", error=str(e))
            return None

    def _analyze_module(self, tree: ast.Module, file_path: str, source: str) -> ParsedModule:
        """Analyze an AST module and extract all components."""
        module = ParsedModule(
            file_path=file_path,
            total_lines=source.count("\n") + 1,
        )

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module.imports.extend(self._extract_imports(node))

            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                module.functions.append(self._extract_function(node))

            elif isinstance(node, ast.ClassDef):
                module.classes.append(self._extract_class(node))

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module.global_variables.append(target.id)

        logger.debug(
            "Module parsed",
            file=file_path,
            functions=len(module.functions),
            classes=len(module.classes),
            imports=len(module.imports),
        )
        return module

    def _extract_imports(self, node: ast.Import | ast.ImportFrom) -> list[str]:
        """Extract import statements."""
        imports = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        return imports

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ParsedFunction:
        """Extract function metadata from an AST node."""
        args = []
        for arg in node.args.args:
            if arg.arg != "self":
                args.append(arg.arg)

        return_annotation = None
        if node.returns:
            return_annotation = ast.unparse(node.returns)

        decorators = [ast.unparse(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        return ParsedFunction(
            name=node.name,
            args=args,
            return_annotation=return_annotation,
            docstring=docstring,
            decorators=decorators,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            complexity=self._estimate_complexity(node),
        )

    def _extract_class(self, node: ast.ClassDef) -> ParsedClass:
        """Extract class metadata from an AST node."""
        bases = [ast.unparse(base) for base in node.bases]
        decorators = [ast.unparse(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func = self._extract_function(item)
                func.is_method = True
                methods.append(func)

        return ParsedClass(
            name=node.name,
            bases=bases,
            docstring=docstring,
            methods=methods,
            decorators=decorators,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )

    def _estimate_complexity(self, node: ast.AST) -> int:
        """Estimate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
