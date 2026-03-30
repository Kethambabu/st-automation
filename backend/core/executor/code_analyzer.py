"""
Smart Code Analyzer for FastAPI Projects

Analyzes Python source code to extract:
- FastAPI routes and their HTTP methods
- Pydantic models and their schemas
- Route-to-model mappings
- Request/response types
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Iterable
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class RouteInfo:
    """Information about a single API route."""
    
    def __init__(
        self,
        method: str,
        path: str,
        function_name: str,
        file_path: Path,
        parameters: Dict[str, str] = None,
        request_model: Optional[str] = None,
    ):
        self.method = method.upper()
        self.path = path
        self.function_name = function_name
        self.file_path = file_path
        self.parameters = parameters or {}  # {param_name: type}
        self.request_model = request_model  # Name of Pydantic model
    
    def __repr__(self):
        return f"RouteInfo({self.method} {self.path})"


class PydanticSchema:
    """Information about a Pydantic model."""
    
    def __init__(self, name: str, fields: Dict[str, str], file_path: Path):
        self.name = name  # Class name
        self.fields = fields  # {field_name: type_str}
        self.file_path = file_path
    
    def __repr__(self):
        return f"PydanticSchema({self.name})"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _iter_python_files(project_dir: Path) -> Iterable[Path]:
    """Iterate all Python files in project (skip common exclusions)."""
    skip_dirs = {
        ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "env",
        "myvenv", "node_modules", "dist", "build", ".tox", ".mypy_cache",
    }
    
    if not project_dir.exists():
        return
    
    for root, dirs, files in __import__("os").walk(project_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if fname.endswith(".py"):
                yield Path(root) / fname


def _extract_type_hint(annotation: ast.expr) -> str:
    """Convert AST annotation to string type hint."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):
        # Safely extract value from Constant node
        value = getattr(annotation, "value", "unknown")
        return str(value)
    elif isinstance(annotation, ast.Attribute):
        # For Optional[X], typing.Optional, etc.
        parts = []
        node = annotation
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))
    elif isinstance(annotation, ast.Subscript):
        # For List[X], Optional[X], etc
        base = _extract_type_hint(annotation.value)
        return f"{base}[...]"
    else:
        return "unknown"


def _extract_type_from_annotation(annotation: Optional[ast.expr]) -> str:
    """Extract Python type from annotation (str, int, bool, etc)."""
    if not annotation:
        return "unknown"
    
    type_str = _extract_type_hint(annotation)
    
    # Map common type names to simple types
    if "str" in type_str.lower():
        return "str"
    elif "int" in type_str.lower():
        return "int"
    elif "float" in type_str.lower():
        return "float"
    elif "bool" in type_str.lower():
        return "bool"
    elif "list" in type_str.lower():
        return "list"
    elif "dict" in type_str.lower():
        return "dict"
    else:
        return type_str


# ============================================================================
# ROUTE EXTRACTOR
# ============================================================================

class FastAPIRouteExtractor(ast.NodeVisitor):
    """AST visitor to extract FastAPI routes."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.routes: List[RouteInfo] = []
        self.current_app_name = "app"  # Assume 'app' unless found differently
    
    def visit_Assign(self, node: ast.Assign):
        """Track variable assignments like: app = FastAPI()"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Look for FastAPI() or Flask() assignments
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        if node.value.func.id in ("FastAPI", "Flask"):
                            self.current_app_name = target.id
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function definitions that have decorators."""
        self._extract_route_from_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Extract async function definitions."""
        self._extract_route_from_function(node)
        self.generic_visit(node)
    
    def _extract_route_from_function(self, func_node):
        """Extract route info from a function with decorators."""
        for decorator in func_node.decorator_list:
            method, path = self._parse_decorator(decorator)
            if method:
                route = RouteInfo(
                    method=method,
                    path=path,
                    function_name=func_node.name,
                    file_path=self.file_path,
                    parameters=self._extract_path_parameters(path),
                    request_model=self._find_request_model(func_node),
                )
                self.routes.append(route)
    
    def _parse_decorator(self, decorator: ast.expr) -> Tuple[Optional[str], str]:
        """Parse decorator like @app.get("/path") to extract method and path."""
        if not isinstance(decorator, ast.Call):
            return None, ""
        
        # Check for form: @app.method(...)
        if isinstance(decorator.func, ast.Attribute):
            attr = decorator.func.attr  # "get", "post", etc
            method = attr.upper()
            
            # Extract path from first argument - safely handle all AST node types
            path = "/"
            if decorator.args:
                path_arg = decorator.args[0]
                
                # Try multiple ways to extract the path value
                if isinstance(path_arg, str):
                    # Already a string (shouldn't happen in AST, but be safe)
                    path = path_arg
                elif isinstance(path_arg, ast.Constant):
                    # Python 3.8+: ast.Constant has .value
                    path = path_arg.value if hasattr(path_arg, "value") else "/"
                elif isinstance(path_arg, ast.Str):
                    # Python 3.7 and earlier: ast.Str has .s
                    path = path_arg.s if hasattr(path_arg, "s") else "/"
                elif hasattr(path_arg, "value"):
                    # Fallback: any node with .value attribute
                    path = path_arg.value
                elif hasattr(path_arg, "s"):
                    # Fallback: any node with .s attribute
                    path = path_arg.s
                else:
                    # Unable to extract, use default
                    logger.debug(
                        f"Could not extract path from decorator arg of type {type(path_arg).__name__}"
                    )
                    path = "/"
                
                # Validate and return
                if isinstance(path, str) and method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"):
                    logger.debug(f"[DEBUG] Extracted route: {method} {path}")
                    return method, path
        
        return None, ""
    
    def _extract_path_parameters(self, path: str) -> Dict[str, str]:
        """Extract path parameters from route like /items/{id} → {id: int}"""
        params = {}
        # Find {param} patterns
        matches = re.findall(r'\{(\w+)\}', path)
        for param in matches:
            # Default to int for ID parameters, str otherwise
            if param.lower() in ("id", "item_id", "todo_id", "user_id"):
                params[param] = "int"
            else:
                params[param] = "str"
        return params
    
    def _find_request_model(self, func_node: ast.FunctionDef) -> Optional[str]:
        """Find the Pydantic model used as request body in function parameters."""
        for arg in func_node.args.args:
            # Skip 'self', 'cls', special params
            if arg.arg in ("self", "cls", "request", "response"):
                continue
            
            # Check if annotation exists and is capitalized (likely a model)
            if arg.annotation:
                type_name = _extract_type_hint(arg.annotation)
                # Filter for likely model names (capitalized)
                if type_name and type_name[0].isupper() and type_name not in ("Request", "Response"):
                    return type_name
        
        return None


# ============================================================================
# PYDANTIC MODEL EXTRACTOR
# ============================================================================

class PydanticModelExtractor(ast.NodeVisitor):
    """AST visitor to extract Pydantic BaseModel definitions."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.models: Dict[str, PydanticSchema] = {}
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class definitions that inherit from BaseModel."""
        # Check if this class inherits from BaseModel
        is_pydantic = False
        for base in node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            
            if base_name == "BaseModel":
                is_pydantic = True
                break
        
        # If it's a Pydantic model, extract fields
        if is_pydantic:
            fields = self._extract_fields(node)
            self.models[node.name] = PydanticSchema(node.name, fields, self.file_path)
        
        self.generic_visit(node)
    
    def _extract_fields(self, class_node: ast.ClassDef) -> Dict[str, str]:
        """Extract field names and types from class body."""
        fields = {}
        
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign):
                # Annotated assignment: field_name: str = "default"
                if isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    field_type = _extract_type_from_annotation(item.annotation)
                    fields[field_name] = field_type
        
        return fields


# ============================================================================
# MAIN ANALYZER
# ============================================================================

class FastAPICodeAnalyzer:
    """
    Analyze FastAPI project to extract routes, schemas, and generate payloads.
    """
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.routes: List[RouteInfo] = []
        self.models: Dict[str, PydanticSchema] = {}
    
    def analyze(self) -> None:
        """Scan project and extract all routes and models."""
        logger.info(f"Analyzing FastAPI project: {self.project_dir}")
        
        for py_file in _iter_python_files(self.project_dir):
            try:
                self._analyze_file(py_file)
            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")
        
        logger.info(f"Found {len(self.routes)} routes and {len(self.models)} models")
    
    def _analyze_file(self, py_file: Path) -> None:
        """Analyze a single Python file."""
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except Exception:
            return
        
        # Extract routes
        route_extractor = FastAPIRouteExtractor(py_file)
        route_extractor.visit(tree)
        self.routes.extend(route_extractor.routes)
        
        # Extract Pydantic models
        model_extractor = PydanticModelExtractor(py_file)
        model_extractor.visit(tree)
        self.models.update(model_extractor.models)
    
    def get_routes(self) -> List[RouteInfo]:
        """Return all detected routes."""
        return self.routes
    
    def get_models(self) -> Dict[str, PydanticSchema]:
        """Return all detected Pydantic models."""
        return self.models
    
    def get_model_by_name(self, name: str) -> Optional[PydanticSchema]:
        """Get a specific model by name."""
        return self.models.get(name)
    
    def generate_payload(self, schema: PydanticSchema) -> Dict[str, Any]:
        """Generate a realistic payload matching the schema."""
        payload = {}
        
        for field_name, field_type in schema.fields.items():
            # Generate appropriate value based on type
            if "bool" in field_type.lower():
                payload[field_name] = True
            elif "int" in field_type.lower():
                payload[field_name] = 1
            elif "float" in field_type.lower():
                payload[field_name] = 1.0
            elif "list" in field_type.lower():
                payload[field_name] = []
            elif "dict" in field_type.lower():
                payload[field_name] = {}
            else:
                # Default to string with field name
                payload[field_name] = f"test_{field_name}"
        
        return payload
    
    def substitute_path_parameters(self, path: str) -> str:
        """Replace path parameters like {id} with realistic values."""
        # Replace {id} patterns with integers
        path = re.sub(r'\{(\w*id\w*)\}', '1', path, flags=re.IGNORECASE)
        # Replace other {param} with generic values
        path = re.sub(r'\{(\w+)\}', 'test', path)
        return path
