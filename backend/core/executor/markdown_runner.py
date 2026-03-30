"""
AI Test Platform — Markdown Test Execution Engine

Reads a Markdown test specification, dynamically generates executable
pytest scripts, executes them in a sandboxed runner, and maps the structured
results back into the requested Passed/Failed dictionary format.
"""

import ast
import tempfile
from pathlib import Path

from core.parser.markdown_parser import MarkdownTestParser
from core.executor.pytest_runner import PytestRunner
from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownTestRunner:
    """End-to-end runner that converts Markdown to pytest code and executes it."""
    
    def __init__(self, target_base_url="http://127.0.0.1:8000"):
        self.parser = MarkdownTestParser()
        self.pytest_runner = PytestRunner()
        self.base_url = target_base_url

    TEST_CASE_TEMPLATE = '''

def {func_name}():
    """{name}"""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        {payload_section}
        url = str(client.base_url.join('{path}'))
        print('Testing:', '{method}', url)
        response = client.request('{method}', '{path}'{payload_arg})
    assert response.status_code == {expected_code}, (
        f'Expected {expected_code} but got {{response.status_code}} from {method} {{url}}. '
        f'Response: {{response.text[:200]}}'
    )
'''

    def _generate_pytest_code(self, parsed_tests: list[dict]) -> str:
        """
        Dynamically synthesize a Python `test_*.py` script from parsed Markdown dictionaries.
        Uses concurrent request templates to make generated test scripts consistent.
        """
        code = [
            "import pytest",
            "import httpx",
            "import json",
            "",
            f"BASE_URL = '{self.base_url.rstrip('/')}'",
            ""
        ]

        for i, tf in enumerate(parsed_tests):
            func_name = f"test_case_{i+1}"
            endpoint_raw = tf.get("endpoint", "")
            method = "GET"
            path = "/"

            if " " in endpoint_raw:
                parts = endpoint_raw.split(" ", 1)
                method = parts[0].strip().upper()
                path = parts[1].strip()
            else:
                path = endpoint_raw.strip()

            if not path:
                path = "/"

            # Normalize path for HTTPX client (avoid double slashes and missing slash)
            if not path.startswith("/"):
                path = "/" + path

            relative_path = path.lstrip("/")
            if relative_path == "":
                relative_path = ""

            # Input handling: parse JSON object; fallback to raw string payload
            input_raw = tf.get("input", "{}")
            payload_arg = ""
            payload_section = ""
            if method in ("POST", "PUT", "PATCH"):
                try:
                    dict_payload = ast.literal_eval(input_raw)
                    if isinstance(dict_payload, dict):
                        payload_section = f"payload = {dict_payload}"
                        payload_arg = ", json=payload"
                    else:
                        payload_section = f"payload = {repr(input_raw)}"
                        payload_arg = ", content=payload"
                except Exception:
                    payload_section = f"payload = {repr(input_raw)}"
                    payload_arg = ", content=payload"

            # Expected status code (default to 200 on parsing failures)
            expected_raw = tf.get("expected", "200")
            expected_code = 200
            try:
                expected_code = int(expected_raw.strip()[:3])
            except Exception:
                expected_code = 200

            # Build each test case from template
            test_block = self.TEST_CASE_TEMPLATE.format(
                func_name=func_name,
                name=tf.get("name", f"Test Case {i+1}"),
                method=method,
                path=relative_path,
                payload_section=payload_section,
                payload_arg=payload_arg,
                expected_code=expected_code,
                status="response.status_code",
                response_body="response.text[:200]",
            )

            code.append(test_block)

        generated_script = "\n".join(code)
        logger.debug(f"Generated pytest script:\n{generated_script}")
        return generated_script

    def run_markdown(self, markdown_content: str) -> dict:
        """
        Parses the Markdown, writes out a temporary pytest script,
        runs it natively, and captures the exact passed/failed outputs.
        """
        # Step 1: Parse Markdown test cases
        parsed_tests = self.parser.parse(markdown_content)
        if not parsed_tests:
            return {"passed": [], "failed": []}

        # Step 2: Convert to executable pytest tests
        pytest_code = self._generate_pytest_code(parsed_tests)

        # Persist the generated test file to the expected workflow path.
        # Some parts of the system expect `storage/generated_tests/test_generated.py`
        # to exist after the code-generation step.
        settings = get_settings()
        generated_dir = Path(settings.GENERATED_DIR)
        generated_dir.mkdir(parents=True, exist_ok=True)
        persistent_test_file = generated_dir / "test_generated.py"
        persistent_test_file.write_text(pytest_code, encoding="utf-8")

        # Create an isolated temporary directory to act as the sandbox
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test_markdown_generated.py"
            test_file.write_text(pytest_code, encoding="utf-8")

            # Step 3: Run the tests automatically
            logger.info("Executing generated pytest suite in sandbox...")
            result = self.pytest_runner.run_tests(test_dir=tmp_path)

            # Step 4: Capture results
            output = {
                "passed": [],
                "failed": []
            }

            for res in result.results:
                # Re-map pytest internal nodeid strings back to the human-readable Markdown test name
                try:
                    idx_str = res.nodeid.split("test_case_")[-1]
                    idx = int(idx_str) - 1
                    test_name = parsed_tests[idx].get("name", f"Test Case {idx+1}")
                except Exception:
                    test_name = res.nodeid
                
                if res.outcome == "passed":
                    output["passed"].append(test_name)
                else:
                    # Simplify stacktrace to just the assertion failure message
                    error_msg = res.longrepr.strip().split("\n")[-1] if res.longrepr else "Failed without stacktrace"
                    output["failed"].append({
                        "name": test_name, 
                        "error": error_msg
                    })

            logger.info("Markdown test execution finalized", passed=len(output["passed"]), failed=len(output["failed"]))
            return output
