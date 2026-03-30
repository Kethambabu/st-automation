"""
AI Test Platform — Review API Endpoints

Provides endpoints to:
  - Upload a Markdown file containing test cases
  - Validate the parsed content
  - Convert the content into structured JSON
"""

import json
from fastapi import APIRouter, File, UploadFile, HTTPException
from core.executor.markdown_parser_v2 import MarkdownTestParserV2
from schemas.review import MarkdownUploadResponse, ParsedTestCase
from utils.logger import get_logger

router = APIRouter(prefix="/review", tags=["Review"])
logger = get_logger(__name__)
parser = MarkdownTestParserV2()


@router.post("/upload", response_model=MarkdownUploadResponse)
async def upload_markdown_tests(file: UploadFile = File(...)):
    """
    Upload a user-edited Markdown test specification.
    
    Parses the Markdown, validates that all required fields 
    (Endpoint, Input, Expected) exist, and returns structured JSON.
    """
    if not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are allowed")
    
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Must be UTF-8.")
        
    # Parse Markdown using v2 parser
    spec = parser.parse(text)
    
    # Check for parsing errors
    if spec.parsing_errors:
        logger.warning(f"Parsing errors encountered: {spec.parsing_errors}")
        raise HTTPException(
            status_code=422, 
            detail=f"Markdown parsing had issues: {'; '.join(spec.parsing_errors)}"
        )
    
    if not spec.test_cases:
        raise HTTPException(
            status_code=422, 
            detail="No valid test cases found in Markdown file. Ensure all test cases have 'Endpoint', 'Input', and 'Expected' fields."
        )
    
    # Convert ParsedTestCase objects to schema response objects
    validated_cases = []
    try:
        for test_case in spec.test_cases:
            # Convert input_data (dict) to JSON string for schema compatibility
            input_str = json.dumps(test_case.input_data) if test_case.input_data else "{}"
            
            # Map ParsedTestCase to ParsedTestCase schema
            validated_cases.append(ParsedTestCase(
                name=test_case.name,
                endpoint=test_case.endpoint,
                method=test_case.method.value if hasattr(test_case.method, 'value') else str(test_case.method),
                input=input_str,
                expected=str(test_case.expected_status),
                description=test_case.description
            ))
    except Exception as e:
        logger.error(f"Error converting test cases: {e}")
        raise HTTPException(
            status_code=422, 
            detail=f"Error processing test cases: {str(e)}"
        )
        
    logger.info(f"Markdown tests validated successfully: {len(validated_cases)} test cases")
    
    
    return MarkdownUploadResponse(
        success=True,
        parsed_count=len(validated_cases),
        test_cases=validated_cases
    )
