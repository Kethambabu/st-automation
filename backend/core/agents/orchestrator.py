"""
AI Test Platform — CrewAI Agent Orchestrator

Defines and coordinates the multi-agent pipeline for test generation:
  1. Analyzer Agent  → Understands code structure
  2. Generator Agent → Creates test cases
  3. Reviewer Agent  → Validates test quality
"""

from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq

from config import get_settings
from utils.logger import get_logger
from core.agents.prompts.analysis import ANALYZER_SYSTEM_PROMPT, ANALYZER_TASK_PROMPT
from core.agents.prompts.generation import GENERATOR_SYSTEM_PROMPT, GENERATOR_TASK_PROMPT
from core.agents.prompts.review import REVIEWER_SYSTEM_PROMPT, REVIEWER_TASK_PROMPT

logger = get_logger(__name__)
settings = get_settings()


def get_llm() -> ChatGroq:
    """Create the LLM instance used by all agents."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )


def create_analyzer_agent(llm: ChatGroq) -> Agent:
    """Create the Code Analyzer agent."""
    return Agent(
        role="Senior Code Analyst",
        goal="Deeply analyze source code to identify all testable components, edge cases, and dependencies",
        backstory=ANALYZER_SYSTEM_PROMPT,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_generator_agent(llm: ChatGroq) -> Agent:
    """Create the Test Generator agent."""
    return Agent(
        role="Expert Test Engineer",
        goal="Generate comprehensive, production-quality pytest test cases",
        backstory=GENERATOR_SYSTEM_PROMPT,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_reviewer_agent(llm: ChatGroq) -> Agent:
    """Create the Test Reviewer agent."""
    return Agent(
        role="Senior QA Reviewer",
        goal="Review and improve generated test cases for correctness, completeness, and best practices",
        backstory=REVIEWER_SYSTEM_PROMPT,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def run_test_generation_pipeline(
    file_path: str,
    source_code: str,
    parsed_structure: dict,
    function_name: str,
    max_tests: int = 3,
    test_types: str = "unit, edge_case",
) -> str:
    """
    Run the full multi-agent test generation pipeline.

    Flow: Analyze → Generate → Review

    Args:
        file_path: Path to the source file
        source_code: The source code content
        parsed_structure: AST-parsed structure as dict
        function_name: Target function name
        max_tests: Maximum tests per function
        test_types: Comma-separated test types

    Returns:
        Final reviewed test code as a string
    """
    llm = get_llm()

    # ── Create Agents ──────────────────────────────────
    analyzer = create_analyzer_agent(llm)
    generator = create_generator_agent(llm)
    reviewer = create_reviewer_agent(llm)

    # ── Define Tasks (Sequential Pipeline) ─────────────
    analysis_task = Task(
        description=ANALYZER_TASK_PROMPT.format(
            file_path=file_path,
            parsed_structure=str(parsed_structure),
            source_code=source_code,
        ),
        expected_output="A detailed JSON analysis of all testable components in the code",
        agent=analyzer,
    )

    generation_task = Task(
        description=GENERATOR_TASK_PROMPT.format(
            file_path=file_path,
            function_name=function_name,
            analysis="{analysis_output}",  # Will be filled by CrewAI context
            source_code=source_code,
            max_tests=max_tests,
            test_types=test_types,
        ),
        expected_output="Complete, runnable pytest test code",
        agent=generator,
        context=[analysis_task],
    )

    review_task = Task(
        description=REVIEWER_TASK_PROMPT.format(
            file_path=file_path,
            source_code=source_code,
            test_code="{generated_tests}",  # Will be filled by CrewAI context
        ),
        expected_output="Improved and validated pytest test code ready for execution",
        agent=reviewer,
        context=[generation_task],
    )

    # ── Create & Run Crew ──────────────────────────────
    crew = Crew(
        agents=[analyzer, generator, reviewer],
        tasks=[analysis_task, generation_task, review_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info(
        "Starting test generation pipeline",
        file_path=file_path,
        function_name=function_name,
    )

    result = crew.kickoff()

    logger.info(
        "Test generation pipeline completed",
        file_path=file_path,
        function_name=function_name,
    )

    return str(result)
