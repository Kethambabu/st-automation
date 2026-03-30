"""
AI Test Platform — Review API Endpoints

Provides endpoints to:
  - Upload a Markdown file containing test cases
  - Validate the parsed content
  - Convert the content into structured JSON
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from core.parser.markdown_parser import MarkdownTestParser
from schemas.review import MarkdownUploadResponse, ParsedTestCase
from utils.logger import get_logger

router = APIRouter(prefix="/review", tags=["Review"])
logger = get_logger(__name__)
parser = MarkdownTestParser()


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
        
    # Convert Markdown to raw dictionaries
    parsed_json = parser.parse(text)
    
    # Validate structure using Pydantic
    validated_cases = []
    try:
        for tc in parsed_json:
            validated_cases.append(ParsedTestCase(**tc))
    except Exception as e:
        raise HTTPException(
            status_code=422, 
            detail=f"Markdown validation failed. Ensure all test cases have 'Endpoint', 'Input', and 'Expected' fields. Error: {e}"
        )
        
    logger.info("Markdown tests validated successfully", count=len(validated_cases))
    
    return MarkdownUploadResponse(
        success=True,
        parsed_count=len(validated_cases),
        test_cases=validated_cases
    )
