"""
AI Test Platform — Test Specification Generator

Uses LangChain (Groq) to generate a comprehensive Markdown test specification
based on the structured project JSON. 

Uses **JSON mode** instead of tool/function calling to avoid parsing
failures when the LLM generates special characters in security test
payloads (e.g. <script>, SQL injection strings).

Categorizes tests into:
  - Functional
  - Edge cases
  - Negative tests
  - Security tests
"""

import json, re
from typing import Literal
from pydantic import BaseModel, Field, ValidationError
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ── 1. Structured Output Schemas (Categorization Logic) ─────────────

class TestCaseSpec(BaseModel):
    """Schema for a single generated test case."""
    category: Literal["Functional", "Edge Case", "Negative", "Security"] = Field(
        description="The category of the test case."
    )
    name: str = Field(description="A descriptive name for the test case (e.g., 'Test Case 1: Valid Login')")
    target: str = Field(description="The API endpoint OR function being tested (e.g., 'POST /users' or 'validate_email()')")
    input_data: str = Field(description="Detailed description of the input payload or arguments.")
    expected_result: str = Field(description="The expected HTTP status code OR return value and side effects.")


class TestSuiteSpec(BaseModel):
    """Schema for the entire generated test suite output by the LLM."""
    test_cases: list[TestCaseSpec] = Field(
        description="A comprehensive list of test cases covering all categories."
    )


# ── 2. LLM Prompt Template ──────────────────────────────────────────

SYSTEM_PROMPT = """Return ONLY valid JSON. No explanation. No text before or after JSON.
Ensure proper commas and quotes. No backslashes. No nested quotes.
Use plain text for all string values."""

USER_PROMPT = """Given these code elements:

{project_json}

Generate test cases JSON. Exactly this format:
{{
  "test_cases": [
    {{"category": "Functional", "name": "test name", "target": "POST /login", "input_data": "username=admin password=pass", "expected_result": "200 OK"}}
  ]
}}

Categories and rules:
- Functional: happy-path calls, expect 200 or 201.
- Edge Case: empty input, missing fields, boundary values, expect 400 or 422.
- Negative: wrong HTTP method or invalid data, expect 405 or 422.
- Security: unauthorized access without token, SQL injection, expect 401 or 403.

Limit: 5 unique test cases total. Each must have a DIFFERENT target or input. Keep values short and simple.
"""


# ── 3. LangChain Python Code ────────────────────────────────────────

def _extract_json_from_text(text: str) -> str:
    """
    Extract a JSON object from LLM output that may contain markdown
    fences or surrounding text.
    """
    # Try to find JSON inside ```json ... ``` blocks
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    # Try to find a raw JSON object
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if m:
        return m.group(1)
    return text


def _safe_parse_suite(raw_text: str) -> TestSuiteSpec:
    """
    Parse LLM output into TestSuiteSpec with multiple fallback strategies.
    """
    cleaned = _extract_json_from_text(raw_text)
    
    # Strategy 1: direct Pydantic parse
    try:
        return TestSuiteSpec.model_validate_json(cleaned)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.warning("Direct JSON parse failed, trying dict parse", error=str(e))

    # Strategy 2: load as Python dict first (more lenient)
    try:
        data = json.loads(cleaned)
        return TestSuiteSpec.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning("Dict parse also failed, trying sanitisation", error=str(e))

    # Strategy 3: sanitise common issues and retry
    try:
        # Fix common JSON issues: trailing commas, single quotes
        sanitised = cleaned
        sanitised = re.sub(r",\s*([}\]])", r"\1", sanitised)  # trailing commas
        sanitised = sanitised.replace("'", '"')                 # single→double quotes
        data = json.loads(sanitised)
        return TestSuiteSpec.model_validate(data)
    except Exception as e:
        logger.error("All JSON parse strategies failed", error=str(e))
        raise ValueError(f"Could not parse LLM response as TestSuiteSpec: {e}")


class SpecGenerator:
    """Generates Markdown test specifications using LangChain and Groq."""

    def __init__(self):
        self.settings = get_settings()
        
        fallback_key = self.settings.GROQ_API_KEY
        if not fallback_key or fallback_key.strip() == "":
             fallback_key = "gsk_dummy_key_please_configure_env_file_properly"

        # Initialize Groq LLM (we don't use Groq's forced JSON mode because
        # its internal validator fails on valid JSON containing security inject payloads)
        self.llm = ChatGroq(
            model=self.settings.GROQ_MODEL,
            api_key=fallback_key,
            temperature=0.3,
            max_tokens=8000,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

        # Simple LCEL chain — no structured_output, we parse manually
        self.chain = self.prompt | self.llm

    def generate_test_suite(self, project_json: str) -> TestSuiteSpec:
        """Invokes the LLM to generate the structured test cases."""
        logger.info("Generating test specifications with Groq")
        
        if "dummy_key" in str(self.llm.groq_api_key):
             mock_response = TestSuiteSpec(
                 test_cases=[
                     TestCaseSpec(
                         category="Functional",
                         name="API Key Configuration Needed",
                         target="Backend .env file",
                         input_data="Missing GROQ_API_KEY in .env",
                         expected_result="Please open the .env file in the backend directory, paste your GROQ_API_KEY, and restart the Uvicorn server to enable AI generation."
                     )
                 ]
             )
             return mock_response

        # Invoke the chain — returns an AIMessage with JSON content
        ai_message = self.chain.invoke({"project_json": project_json})
        raw_text = ai_message.content
        logger.info("LLM response received", length=len(raw_text))

        # Parse the JSON response manually (robust against special chars)
        return _safe_parse_suite(raw_text)


# ── 4. Markdown Generator ───────────────────────────────────────────

def format_as_markdown(test_suite: TestSuiteSpec) -> str:
    """Converts the structured Pydantic models into the requested Markdown format."""
    
    categories = {
        "Functional": [],
        "Edge Case": [],
        "Negative": [],
        "Security": []
    }

    for test in test_suite.test_cases:
        if test.category in categories:
            categories[test.category].append(test)
        else:
            categories["Functional"].append(test)

    md_lines = ["# Comprehensive Test Specification\n"]

    for category, tests in categories.items():
        if not tests:
            continue
            
        md_lines.append(f"## {category} Tests\n")
        
        for i, t in enumerate(tests, 1):
            md_lines.append(f"### {t.name}")
            md_lines.append(f"**Target**: `{t.target}`")
            md_lines.append(f"**Input**: {t.input_data}")
            md_lines.append(f"**Expected**: {t.expected_result}")
            md_lines.append("")  # Empty line for spacing
            
    return "\n".join(md_lines)
