"""
AI Test Platform — Test Generation Endpoints

Connects the parsed project JSON to the SpecGenerator LLM module to 
produce written Markdown tests.

Handles large codebases by summarising and chunking the analysis data
so that each request to the Groq API stays within payload limits.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json, asyncio, math

from models.base import get_db
from models.project import Project
from core.analyzer import ProjectAnalyzer
from core.agents.spec_generator import SpecGenerator, TestSuiteSpec, format_as_markdown
from schemas.analysis import AnalysisSummary
from pydantic import BaseModel
from utils.logger import get_logger

router = APIRouter(prefix="/generation", tags=["Generation"])
logger = get_logger(__name__)

# ── Chunking helpers ────────────────────────────────────────────────

# Maximum number of items (functions / classes) per LLM chunk.
# Groq's llama-3.3-70b-versatile accepts ~128 k tokens but the *request
# entity* limit is lower (~4-6 MB).  Keeping chunks small guarantees we
# stay well within both limits.
CHUNK_SIZE = 10


def _summarise_analysis(analysis) -> dict:
    """
    Build a *lightweight* dict from the full ProjectAnalysis.

    Only keeps the fields the LLM actually needs to write tests:
      - APIs:      path, method, function_name, args
      - Functions: name, args, return_type, decorators, is_async
      - Classes:   name, bases, methods (name + args only)

    Everything else (docstrings, line numbers, imports,
    global_variables, complexity …) is stripped to save tokens.
    """
    # HARD LIMITS: Truncate massive codebases for stability limits.
    # Sending 16,000+ items to an LLM sequentially takes 60+ minutes 
    # and will timeout the web connection. We sample the first few items.
    apis = [
        {
            "path": a.path,
            "method": a.http_method,
            "function": a.function_name,
            "args": a.args,
            "framework": a.framework,
        }
        for a in analysis.apis
    ][:20]

    # Only keep top-level (non-method) functions to avoid duplicates
    functions = [
        {
            "name": f.name,
            "args": f.args,
            "returns": f.return_type,
            "async": f.is_async,
            "decorators": f.decorators[:2],   # keep max 2 decorators
        }
        for f in analysis.functions
        if not f.is_method
    ][:30]

    classes = [
        {
            "name": c.name,
            "bases": c.bases,
            "methods": [
                {"name": m.name, "args": m.args}
                for m in (c.methods or [])[:5]     # cap methods per class
            ],
        }
        for c in analysis.classes
    ][:10]

    return {"apis": apis, "functions": functions, "classes": classes}


def _make_chunks(summary: dict) -> list[str]:
    """
    Split the summarised dict into JSON string chunks that each
    contain at most CHUNK_SIZE items (functions + classes combined).

    APIs are always included in *every* chunk (they are few and
    critical for generating security / endpoint tests).
    """
    apis = summary["apis"]
    functions = summary["functions"]
    classes = summary["classes"]

    # Combine functions and classes into one list of (type, item) pairs
    items: list[tuple[str, dict]] = []
    for f in functions:
        items.append(("function", f))
    for c in classes:
        items.append(("class", c))

    if not items:
        # Nothing to send — just APIs
        return [json.dumps({"apis": apis, "functions": [], "classes": []}, default=str)]

    num_chunks = max(1, math.ceil(len(items) / CHUNK_SIZE))
    chunks: list[str] = []
    for i in range(num_chunks):
        batch = items[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
        chunk_funcs = [it for tp, it in batch if tp == "function"]
        chunk_classes = [it for tp, it in batch if tp == "class"]
        chunk_dict = {
            "apis": apis,       # always include APIs
            "functions": chunk_funcs,
            "classes": chunk_classes,
            "chunk": f"{i + 1}/{num_chunks}",
        }
        chunks.append(json.dumps(chunk_dict, default=str))

    return chunks


# ── Response model ──────────────────────────────────────────────────

class GenerationResponse(BaseModel):
    project_id: str
    status: str
    markdown_output: str


# ── Endpoint ────────────────────────────────────────────────────────

@router.post("/{project_id}", response_model=GenerationResponse)
async def generate_tests(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Triggers AI test generation for the specified analyzed project.
    Converts the AST JSON structure into natural Language Tests.

    Large codebases are automatically chunked so that each Groq API
    request stays within the payload size limit.
    """
    # 1. Fetch project to ensure it exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.storage_path or project.status not in ("PARSED", "UPLOADED", "PARSING", "FAILED"):
        raise HTTPException(status_code=400, detail="Project not fully processed or missing extraction path.")

    try:
        _analyzer = ProjectAnalyzer()
        _generator = SpecGenerator()

        # 2. Re-grab the full AST analysis
        analysis = _analyzer.analyze_directory(
            directory=project.storage_path,
            project_name=project.name,
            project_id=project_id,
        )

        # 3. Build a *lightweight* summary and split into chunks
        summary = _summarise_analysis(analysis)
        chunks = _make_chunks(summary)
        logger.info(
            "Prepared LLM chunks",
            project_id=project_id,
            total_functions=len(summary["functions"]),
            total_classes=len(summary["classes"]),
            total_apis=len(summary["apis"]),
            num_chunks=len(chunks),
        )

        # 4. Send each chunk to the LLM and collect test cases
        all_test_cases = []
        for idx, chunk_json in enumerate(chunks):
            logger.info("Generating tests for chunk", chunk=f"{idx+1}/{len(chunks)}", project_id=project_id)
            suite = await asyncio.to_thread(_generator.generate_test_suite, chunk_json)
            all_test_cases.extend(suite.test_cases)

        # Deduplicate: keep first occurrence of each (target, category, expected) combination
        seen = set()
        unique_test_cases = []
        for tc in all_test_cases:
            key = (tc.target.strip().lower(), tc.category, tc.expected_result.strip().lower())
            if key not in seen:
                seen.add(key)
                unique_test_cases.append(tc)

        merged_suite = TestSuiteSpec(test_cases=unique_test_cases)

        # 5. Format as Markdown
        md_text = await asyncio.to_thread(format_as_markdown, merged_suite)

        return GenerationResponse(
            project_id=project_id,
            status="GENERATED",
            markdown_output=md_text,
        )

    except Exception as e:
        logger.error("Test generation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

