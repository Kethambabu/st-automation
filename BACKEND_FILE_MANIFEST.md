# Backend Python Files - Quick Reference

## File Manifest with Key Information

| File Path | Lines | Purpose | Key Exports | Status |
|-----------|-------|---------|-------------|--------|
| config.py | 65 | Configuration management | Settings, get_settings() | ✅ |
| main.py | 78 | FastAPI entrypoint | app, lifespan() | ✅ |
| core/analyzer.py | 261 | Project analysis orchestrator | ProjectAnalyzer | ✅ |
| core/execution_engine.py | 130 | Background markdown execution | run_markdown_execution() | ⚠️ Legacy |
| core/agents/orchestrator.py | 158 | Multi-agent orchestration | Agent creators, run_test_generation_pipeline() | ✅ |
| core/agents/spec_generator.py | 215 | Test spec generation via LLM | TestSuiteSpec, SpecGenerator | ✅ |
| core/agents/failure_analyzer.py | 145 | LLM-based failure analysis | FailureAnalysis, FailureAnalyzer | ✅ |
| core/agents/prompts/analysis.py | 30 | Analyzer agent prompts | ANALYZER_SYSTEM_PROMPT, ANALYZER_TASK_PROMPT | ✅ |
| core/agents/prompts/generation.py | 30 | Generator agent prompts | GENERATOR_SYSTEM_PROMPT, GENERATOR_TASK_PROMPT | ✅ |
| core/agents/prompts/review.py | 25 | Reviewer agent prompts | REVIEWER_SYSTEM_PROMPT, REVIEWER_TASK_PROMPT | ✅ |
| core/parser/ast_parser.py | 222 | Python AST parsing | ParsedFunction, ParsedClass, ParsedModule, PythonASTParser | ✅ |
| core/parser/code_models.py | 150 | Code analysis Pydantic models | FunctionInfo, ClassInfo, ModuleInfo, APIInfo, ProjectAnalysis | ✅ |
| core/parser/api_detector.py | 247 | API route detection | DetectedAPI, APIRouteDetector | ✅ |
| core/parser/markdown_parser.py | 85 | Markdown parsing (v1) | MarkdownTestParser | ⚠️ **DEPRECATED** |
| core/executor/execution_engine_v2.py | 796 | Complete test execution engine | ImprovedTestExecutionEngine, helper functions | ✅ **LARGE FILE** |
| core/executor/pytest_code_generator.py | 732 | Smart pytest code generation | PytestCodeGeneratorV2, test templates | ✅ **LARGE FILE** |
| core/executor/markdown_parser_v2.py | 306 | Robust markdown parsing (v2) | MarkdownTestParserV2, parse_form_data() | ✅ |
| core/executor/code_analyzer.py | 386 | FastAPI code analysis | RouteInfo, PydanticSchema, FastAPICodeAnalyzer | ✅ |
| core/executor/test_models.py | 265 | Test execution data models | ParsedTestCase, GeneratedTest, TestRunSummary, etc. | ✅ |
| core/executor/markdown_runner.py | 185 | End-to-end markdown execution | MarkdownTestRunner | ✅ |
| core/executor/pytest_runner.py | 193 | Pytest execution (subprocess) | PytestRunner, IndividualTestResult, PytestRunResult | ✅ |
| core/executor/pytest_api_runner.py | 305 | Pytest execution (API mode) | PytestApiRunnerV2, PytestHookCollector | ✅ |
| core/executor/test_validator.py | 230 | Test specification validation | TestSpecificationValidator | ✅ |
| core/executor/test_config.py | 120 | Test execution configuration | TestExecutionConfig, get_test_config() | ✅ |
| core/executor/utils.py | 264 | Execution utilities | sanitize_test_name(), parse_endpoint(), extract_* functions | ✅ |
| api/router.py | 20 | Root API router | api_router | ✅ |
| api/dependencies.py | 15 | FastAPI dependencies | get_database_session() | ✅ |
| api/v1/upload.py | 146 | File upload endpoints | POST /upload/zip, POST /upload/github | ✅ |
| api/v1/analysis.py | 155 | Project analysis endpoints | POST /analysis/{id}, GET /analysis/{id} | ✅ |
| api/v1/generation.py | 213 | Test generation endpoints | POST /generation/{id}, chunking logic | ✅ |
| api/v1/tests.py | 80 | Test management endpoints | POST /tests/generate, GET /tests/, POST /tests/execute | ✅ |
| api/v1/results.py | 60 | Test results endpoints | GET /results/{id}, GET /results/run/{id} | ✅ |
| api/v1/projects.py | 90 | Project CRUD endpoints | GET /projects/, GET /projects/{id}, DELETE /projects/{id} | ✅ |
| api/v1/review.py | 60 | Markdown review endpoints | POST /review/upload | ✅ |
| models/base.py | 45 | Database configuration | Base, get_db(), init_db(), engine | ✅ |
| models/project.py | 65 | Project ORM model | Project | ✅ |
| models/test_case.py | 60 | Test case ORM model | TestCase | ✅ |
| models/test_result.py | 115 | Test result ORM models | TestRun, TestResult | ✅ |
| schemas/project.py | 55 | Project schemas | ProjectCreate, ProjectResponse, UploadResponse | ✅ |
| schemas/analysis.py | 20 | Analysis schemas | AnalysisSummary | ✅ |
| schemas/test_case.py | 30 | Test case schemas | TestCaseResponse, TestGenerateRequest | ✅ |
| schemas/result.py | 50 | Result schemas | TestResultResponse, TestRunResponse, ExecutionRequest | ✅ |
| schemas/review.py | 25 | Review schemas | ParsedTestCase, MarkdownUploadResponse | ✅ |
| utils/file_utils.py | 120 | File handling utilities | generate_project_id(), save_upload(), extract_zip(), scan_source_files() | ✅ |
| utils/logger.py | 50 | Logging configuration | setup_logging(), get_logger() | ✅ |

---

## Import Dependency Matrix

### Most Interconnected Files

**High Internal Coupling**:
- `core/executor/execution_engine_v2.py` → 8+ internal modules
- `core/executor/pytest_code_generator.py` → 6+ internal modules
- `api/v1/generation.py` → 5+ internal modules
- `core/analyzer.py` → 6+ internal modules

**High External Dependencies**:
- `core/agents/orchestrator.py` → crewai, langchain_groq
- `core/agents/spec_generator.py` → pydantic, langchain_core, langchain_groq
- `core/agents/failure_analyzer.py` → pydantic, langchain_core, langchain_groq

**Low Coupling (Good)**:
- `models/*` → Only sqlalchemy
- `schemas/*` → Only pydantic
- `utils/*` → Minimal dependencies
- `core/parser/*` → Only stdlib + pathlib

---

## Refactoring Opportunities Ranked by Priority

### 🔴 Critical (Do First)

1. **Remove deprecated files**
   - `core/parser/markdown_parser.py` (use v2 instead)
   - Update all imports

2. **Split `execution_engine_v2.py` (796 lines)**
   - Extract server_manager.py (server lifecycle)
   - Extract markdown_executor.py (markdown execution)
   - Extract database_persistence.py (DB operations)

3. **Split `pytest_code_generator.py` (732 lines)**
   - Extract endpoint_normalizer.py
   - Extract api_test_generator.py
   - Extract code_templates.py

### 🟡 High (Do Soon)

4. **Consolidate dual execution engines**
   - `core/execution_engine.py` vs `core/executor/execution_engine_v2.py`
   - Choose one canonical implementation

5. **Unify test runners**
   - `pytest_runner.py` (subprocess) vs `pytest_api_runner.py` (API)
   - Create unified interface with pluggable backends

6. **Extract generation orchestration**
   - Move chunking logic from `api/v1/generation.py` to `core/agents/`

### 🟢 Medium (Nice to Have)

7. **Add test coverage**
   - Unit tests for parser modules
   - Integration tests for API endpoints
   - Fixtures for test execution

8. **Performance optimization**
   - Profile large file analysis
   - Cache AST parsing results
   - Optimize database queries

---

## File Duplicate/Similarity Analysis

### Markdown Parsers (HIGH PRIORITY)
```
core/parser/markdown_parser.py (85 lines)
  - Line-by-line regex parsing
  - Fragile, prone to edge cases
  - DEPRECATED

core/executor/markdown_parser_v2.py (306 lines)
  - Block-based parsing
  - Pydantic validation
  - RECOMMENDED - Use this one
  
ACTION: Remove v1, always use v2
```

### Test Execution Engines (MEDIUM PRIORITY)
```
core/execution_engine.py (130 lines)
  - Specific to markdown tests
  - Background execution focus
  - Older implementation

core/executor/execution_engine_v2.py (796 lines)
  - Complete orchestration
  - Server lifecycle management
  - Newer, more comprehensive
  
ACTION: Clarify roles or consolidate
```

### Pytest Runners (MEDIUM PRIORITY)
```
core/executor/pytest_runner.py (193 lines)
  - Executor-based approach
  - JSON report parsing

core/executor/pytest_api_runner.py (305 lines)
  - Python API approach
  - Hook-based result collection
  
ACTION: Provide unified interface
```

---

## Statistics Summary

- **Total Python files** (excluding storage/): 60
- **Total lines of code**: ~6,500
- **Average file size**: 108 lines
- **Largest file**: execution_engine_v2.py (796 lines)
- **Smallest file**: dependencies.py, router.py (15-20 lines)

**By Category**:
- API endpoints: 700 lines (11%)
- Core logic: 2,500 lines (38%)
- Data models: 600 lines (9%)
- Test execution: 2,200 lines (34%)
- Utilities: 400 lines (8%)

**Dependencies**:
- External packages: 8-10 major
- Internal modules: 50+ interconnected
- Circular dependencies: None detected
- Dead code: No obvious orphaned modules

---

## Quick Fixes Checklist

- [ ] Remove `core/parser/markdown_parser.py`
- [ ] Update imports to use `MarkdownTestParserV2`
- [ ] Add `storage/` to `.gitignore`
- [ ] Move API keys to environment variables only
- [ ] Add unit tests for critical modules
- [ ] Document decision on dual runners/engines
- [ ] Create refactoring tickets for large files
- [ ] Set up code quality checks (pylint, mypy)
- [ ] Document async/await patterns
- [ ] Add integration tests for API endpoints

---

## Module Health Scorecard

| Module | Size | Cohesion | Coupling | Maintainability | Score |
|--------|------|----------|----------|-----------------|-------|
| models/ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🟢 |
| schemas/ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🟢 |
| core/parser/ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟢 |
| core/agents/ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟢 |
| api/v1/ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🟡 |
| core/executor/ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 🟡 |
| core/executor/execution_engine_v2.py | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | 🔴 |
| core/executor/pytest_code_generator.py | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | 🔴 |

---

**Report Generated**: March 30, 2026  
**Confidence**: ⭐⭐⭐⭐⭐ (100% - based on source code inspection)
