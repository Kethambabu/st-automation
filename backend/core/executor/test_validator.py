"""
Test Specification Validator

Validates test markdown before execution to catch issues early.
Prevents 404 errors and other common mistakes.
"""

from typing import List, Dict, Tuple
import re
from core.executor.test_models import ParsedTestCase
from utils.logger import get_logger

logger = get_logger(__name__)


class TestSpecificationValidator:
    """Validates test specifications before execution."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, test_cases: List[ParsedTestCase]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate test cases.
        
        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        if not test_cases:
            self.errors.append("No test cases provided")
            return False, self.errors, self.warnings
        
        for idx, test in enumerate(test_cases):
            self._validate_test_case(test, idx)
        
        is_valid = len(self.errors) == 0
        
        logger.info(
            f"Validation complete: {len(test_cases)} tests, "
            f"{len(self.errors)} errors, {len(self.warnings)} warnings"
        )
        
        return is_valid, self.errors, self.warnings
    
    def _validate_test_case(self, test: ParsedTestCase, idx: int) -> None:
        """Validate a single test case."""
        prefix = f"Test {idx + 1} ({test.name})"
        
        # Validate endpoint format
        if not test.endpoint:
            self.errors.append(f"{prefix}: Endpoint is empty")
            return
        
        if not test.endpoint.startswith("/"):
            self.errors.append(f"{prefix}: Endpoint must start with / (got: {test.endpoint})")
            return
        
        # Check for common mistakes
        if test.endpoint.startswith("/api/v1/"):
            self.warnings.append(
                f"{prefix}: Endpoint starts with /api/v1/ but base_url already includes it. "
                f"Use {test.endpoint[8:]} instead"
            )
        
        if "http://" in test.endpoint or "https://" in test.endpoint:
            self.errors.append(
                f"{prefix}: Endpoint contains full URL but should be just path. "
                f"Bad: {test.endpoint}, Good: /some/path"
            )
        
        # Validate status code
        if test.expected_status < 100 or test.expected_status > 599:
            self.errors.append(
                f"{prefix}: Expected status code {test.expected_status} is invalid. "
                f"Must be 100-599"
            )
        
        # Validate method
        if test.method.value not in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
            self.errors.append(f"{prefix}: Invalid HTTP method {test.method.value}")
        
        # Warn about potentially missing endpoints
        self._warn_suspicious_endpoints(test, prefix)
    
    def _warn_suspicious_endpoints(self, test: ParsedTestCase, prefix: str) -> None:
        """Warn about endpoints that might not exist."""
        suspicious = [
            ("/health", "Health check is at root /health, not under /api/v1"),
            ("/docs", "Swagger UI is at root /docs, not under /api/v1"),
            ("/openapi.json", "OpenAPI schema is at root /openapi.json"),
        ]
        
        for endpoint, message in suspicious:
            if test.endpoint == endpoint:
                self.warnings.append(f"{prefix}: {message}")
    
    def get_full_url(self, test: ParsedTestCase) -> str:
        """Get the full URL that will be tested."""
        return f"{self.base_url}{test.endpoint}"
    
    def print_validation_report(self) -> None:
        """Print a human-readable validation report."""
        print("\n" + "="*70)
        print("TEST SPECIFICATION VALIDATION REPORT")
        print("="*70)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        if not self.errors:
            print("\n✅ Validation PASSED - All tests ready to execute")
        else:
            print(f"\n❌ Validation FAILED - Fix {len(self.errors)} error(s) before running")
        
        print("="*70 + "\n")


class FastAPIRouteValidator:
    """Optional: Validate endpoints exist on the actual FastAPI server."""
    
    def __init__(self, base_url: str, schema_url: str = "/openapi.json"):
        self.base_url = base_url
        self.schema_url = schema_url
        self.available_routes: Dict[str, List[str]] = {}
        self._loaded = False
    
    async def load_routes_async(self):
        """Load available routes from OpenAPI schema (async)."""
        try:
            import httpx
            schema_full_url = self.base_url.replace("/api/v1", "") + self.schema_url
            
            async with httpx.AsyncClient() as client:
                response = await client.get(schema_full_url, timeout=5)
                response.raise_for_status()
                
                schema = response.json()
                
                # Extract paths from OpenAPI schema
                paths = schema.get("paths", {})
                for path, methods in paths.items():
                    self.available_routes[path] = list(methods.keys())
                
                self._loaded = True
                logger.info(f"Loaded {len(self.available_routes)} routes from FastAPI server")
                
        except Exception as e:
            logger.warning(f"Could not load OpenAPI schema: {e}")
            self._loaded = False
    
    def validate_endpoint_exists(self, endpoint: str, method: str) -> bool:
        """Check if endpoint exists in available routes."""
        if not self._loaded:
            logger.warning("Routes not loaded - skipping validation")
            return True
        
        # Normalize path (remove trailing slash for comparison)
        endpoint_normalized = endpoint.rstrip("/") or "/"
        
        # Check exact match
        if endpoint_normalized in self.available_routes:
            methods = self.available_routes[endpoint_normalized]
            return method.lower() in methods or "parameters" in str(methods)
        
        # Check path parameters (e.g., /items/{id})
        for available_path, methods in self.available_routes.items():
            if self._paths_match_with_params(endpoint_normalized, available_path):
                return method.lower() in methods or "parameters" in str(methods)
        
        return False
    
    @staticmethod
    def _paths_match_with_params(test_path: str, available_path: str) -> bool:
        """Check if paths match with path parameters."""
        test_parts = test_path.split("/")
        avail_parts = available_path.split("/")
        
        if len(test_parts) != len(avail_parts):
            return False
        
        for test_part, avail_part in zip(test_parts, avail_parts):
            # Skip if available has path parameter placeholder
            if "{" in avail_part and "}" in avail_part:
                continue
            if test_part != avail_part:
                return False
        
        return True


# Example usage in execution pipeline:

async def validate_tests_before_execution(test_cases: List[ParsedTestCase], base_url: str) -> bool:
    """
    Validate tests before execution.
    
    Usage:
        from core.executor.test_validator import validate_tests_before_execution
        
        is_valid = await validate_tests_before_execution(parsed_tests, config.target_base_url)
        if not is_valid:
            return {"success": False, "error": "Invalid test specification"}
    """
    # Basic validation
    validator = TestSpecificationValidator(base_url)
    is_valid, errors, warnings = validator.validate(test_cases)
    
    validator.print_validation_report()
    
    if errors:
        logger.error(f"Test validation failed: {errors}")
        return False
    
    if warnings:
        logger.warning(f"Test validation warnings: {warnings}")
    
    return True
