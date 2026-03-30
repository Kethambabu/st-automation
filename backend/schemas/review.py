"""
AI Test Platform — Review Interface Schemas
"""

import json
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator

class ParsedTestCase(BaseModel):
    """Schema for a test case successfully parsed from Markdown."""
    name: str = Field(default="Unnamed Test Case")
    endpoint: str
    input: str
    expected: str
    description: Optional[str] = Field(default=None)
    method: Optional[str] = Field(default="GET")
    
    @field_validator('input', mode='before')
    @classmethod
    def validate_input(cls, v: Union[str, dict]) -> str:
        """Ensure input is always a JSON string."""
        if isinstance(v, dict):
            return json.dumps(v)
        if isinstance(v, str):
            # Validate it's valid JSON if it looks like JSON
            if v.strip().startswith('{'):
                try:
                    json.loads(v)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in input field: {str(e)}")
            return v
        if v is None:
            return "{}"
        return str(v)

class MarkdownUploadResponse(BaseModel):
    """Schema for the API response after uploading a Markdown file."""
    success: bool
    parsed_count: int
    test_cases: list[ParsedTestCase]
