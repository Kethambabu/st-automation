"""
AI Test Platform — Review Interface Schemas
"""

from pydantic import BaseModel, Field

class ParsedTestCase(BaseModel):
    """Schema for a test case successfully parsed from Markdown."""
    name: str = Field(default="Unnamed Test Case")
    endpoint: str
    input: str
    expected: str

class MarkdownUploadResponse(BaseModel):
    """Schema for the API response after uploading a Markdown file."""
    success: bool
    parsed_count: int
    test_cases: list[ParsedTestCase]
