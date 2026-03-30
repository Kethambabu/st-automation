"""
AI Test Platform — Automated Failure Analysis Engine

Uses LangChain (Groq) to intelligently debug failed test test cases.
Parses the exact differences between expected and actual output, reads
stack traces/logs, and provides a root cause analysis and suggested fix.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ── 1. Structured Output Schema ──────────────────────────────────────

class FailureAnalysis(BaseModel):
    """Structured response schema forcing the LLM to output the requested format."""
    failure_reason: str = Field(
        description="A clear, concise explanation of the failure (e.g. 'API returned 500 instead of 200.')."
    )
    possible_cause: str = Field(
        description="The underlying technical root cause based on the logs or data discrepancy (e.g. 'Null pointer in authentication module')."
    )
    suggested_fix: str = Field(
        description="Actionable advice and code snippets on how to fix the issue (e.g. 'Validate password input before database query.')."
    )


# ── 2. LLM Prompt Templates ──────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI Debugging Assistant and Senior Software Architect.
Your task is to analyze a failing automated test case and determine the root cause constraint.

You must output your analysis exactly according to the structured JSON schema requested.
Keep your analysis highly technical, focused, and directly actionable.
"""

USER_PROMPT = """Analyze the following test failure:

--- TEST CASE DETAILS ---
{test_case}

--- EXPECTED OUTPUT ---
{expected_output}

--- ACTUAL OUTPUT / ERROR ---
{actual_output}

--- SYSTEM LOGS / TRACE ---
{logs}
"""


# ── 3. Failure Analyzer Module ───────────────────────────────────────

class FailureAnalyzer:
    """Invokes the LLM to debug a failing test suite."""

    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGroq(
            model=self.settings.GROQ_MODEL,
            api_key=self.settings.GROQ_API_KEY,
            temperature=0.1,  # Keep temperature low for analytical accuracy
        )
        self.structured_llm = self.llm.with_structured_output(FailureAnalysis)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])
        self.chain = self.prompt | self.structured_llm

    def analyze_failure(self, test_case: str, expected_output: str, actual_output: str, logs: str = "No logs provided.") -> FailureAnalysis:
        """
        Executes the failure analysis chain.
        """
        logger.info("Triggering LLM Failure Analysis...")
        return self.chain.invoke({
            "test_case": test_case,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "logs": logs
        })

    def format_as_text(self, analysis: FailureAnalysis) -> str:
        """Formats the structured LLM output into the human-readable text block requested."""
        return (
            f"Failure Reason:\n{analysis.failure_reason}\n\n"
            f"Possible Cause:\n{analysis.possible_cause}\n\n"
            f"Suggested Fix:\n{analysis.suggested_fix}\n"
        )


# ── 4. Integration with Test Results ─────────────────────────────────

def analyze_test_run(failed_tests: list[Dict[str, Any]], parsed_markdown_specs: list[Dict[str, Any]], system_logs: str = "") -> Dict[str, str]:
    """
    Integration hook. 
    Matches the failing tests returned by PytestRunner to their original 
    Markdown specs, and runs the AI Failure Analyzer on each.
    
    Args:
        failed_tests: The "failed" array from `MarkdownTestRunner.run_markdown()`
        parsed_markdown_specs: The original dictionaries parsed by `MarkdownTestParser`
        system_logs: Any recent backend logs or stacktraces available
        
    Returns:
        A dictionary mapping the test name to the human-readable AI analysis string.
    """
    analyzer = FailureAnalyzer()
    analysis_reports = {}

    for failing_test in failed_tests:
        test_name = failing_test.get("name", "Unknown Test")
        actual_error = failing_test.get("error", "No error captured.")
        
        # Look up the original intended spec from the markdown
        spec = next((t for t in parsed_markdown_specs if t.get("name") == test_name), {})
        
        # Build prompt inputs
        tc_details = f"Endpoint: {spec.get('endpoint', 'N/A')}\nInput: {spec.get('input', 'N/A')}"
        expected = spec.get("expected", "N/A")
        
        # Run AI debugger
        try:
            report_struct = analyzer.analyze_failure(
                test_case=f"Name: {test_name}\n{tc_details}",
                expected_output=expected,
                actual_output=actual_error,
                logs=system_logs
            )
            analysis_reports[test_name] = analyzer.format_as_text(report_struct)
        except Exception as e:
             logger.error("AI Failure Analysis failed", error=str(e), test=test_name)
             analysis_reports[test_name] = f"Failure Reason:\nCould not run AI analysis: {e}"

    return analysis_reports
