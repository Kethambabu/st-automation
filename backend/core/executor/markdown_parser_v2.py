"""
AI Test Platform — Improved Markdown Test Parser

Replaces the fragile line-by-line regex parser with a robust block-based parser.
Uses structured validation with Pydantic models.
"""

import re
from typing import Optional, List, Dict, Any
from core.executor.test_models import (
    ParsedTestCase, 
    ParsedTestSpecification,
    HTTPMethod,
)
from core.executor.utils import (
    parse_endpoint,
    extract_status_code,
    extract_json_payload,
    extract_key_value_pairs,
    split_into_blocks,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_form_data(s: str) -> Optional[Dict[str, Any]]:
    """
    Very small parser for whitespace-separated key=value pairs.

    Example:
      "username=admin password=pass" -> {"username": "admin", "password": "pass"}
    """
    try:
        if not s or not s.strip():
            return None

        # Allow &-separated strings too by treating '&' as whitespace.
        tokens = s.strip().replace("&", " ").split()
        parsed: Dict[str, Any] = {}
        for tok in tokens:
            if "=" not in tok:
                continue
            k, v = tok.split("=", 1)
            k = k.strip().strip("`").strip()
            v = v.strip().strip("`").strip()
            if k:
                parsed[k] = v

        return parsed or None
    except Exception:
        return None


class MarkdownTestParserV2:
    """
    Improved Markdown test specification parser.
    
    Converts human-readable Markdown into structured, validated test cases.
    
    Features:
    - Block-based parsing (more robust than line-by-line)
    - Pydantic validation (type safety)
    - Detailed error reporting
    - Flexible formatting
    
    Expected Markdown format:
    
    ### Test Case Name
    **Endpoint**: GET /api/users
    **Input**: {"id": 123}
    **Expected**: 200 OK
    **Description**: Optional description
    
    ### Another Test
    **Endpoint**: POST /api/data
    **Input**: {"name": "John"}
    **Expected**: 201
    """
    
    # Pattern to detect test case heading
    # Only treat `### ...` lines as test case blocks.
    # This avoids parsing unrelated `# Title` or `## Section` headings.
    HEADING_PATTERN = r'^#{3}\s+(.+?)(?:\s*:)?$'
    
    def __init__(self):
        self.errors: List[str] = []
    
    def parse(self, markdown_content: str) -> ParsedTestSpecification:
        """
        Parse markdown content into structured test specification.
        
        Args:
            markdown_content: Raw markdown text
            
        Returns:
            ParsedTestSpecification with test cases and any parsing errors
        """
        self.errors = []
        test_cases: List[ParsedTestCase] = []
        
        if not markdown_content or not markdown_content.strip():
            self.errors.append("Empty markdown content")
            logger.warning("Empty markdown provided to parser")
            return ParsedTestSpecification(
                test_cases=[],
                raw_content=markdown_content,
                parsing_errors=self.errors,
            )
        
        # Split content into blocks by heading markers
        blocks = self._split_into_test_blocks(markdown_content)
        
        logger.info(f"Found {len(blocks)} potential test blocks")
        
        for block_idx, block in enumerate(blocks):
            try:
                parsed = self._parse_block(block)
                if parsed:
                    test_cases.append(parsed)
                    logger.debug(f"Successfully parsed test block {block_idx}: {parsed.name}")
            except Exception as e:
                error_msg = f"Failed to parse test block {block_idx}: {str(e)}"
                self.errors.append(error_msg)
                logger.warning(error_msg, exc_info=True)
        
        logger.info(
            f"Parsing complete: {len(test_cases)} valid tests, {len(self.errors)} errors"
        )
        
        return ParsedTestSpecification(
            test_cases=test_cases,
            raw_content=markdown_content,
            parsing_errors=self.errors,
        )
    
    def _split_into_test_blocks(self, content: str) -> List[str]:
        """
        Split markdown into test blocks by heading markers.
        
        A test block starts with `### ...` and continues until the next `### ...`.
        """
        lines = content.split('\n')
        blocks = []
        current_block: List[str] = []
        started = False
        
        for line in lines:
            # Check if this line starts a new test block (### only)
            if re.match(self.HEADING_PATTERN, line):
                if started and current_block:
                    blocks.append('\n'.join(current_block))

                # Start new block with heading
                current_block = [line]
                started = True
            else:
                # Ignore everything until we hit the first test heading
                if started:
                    current_block.append(line)
        
        # Don't forget the last block
        if started and current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _parse_block(self, block: str) -> Optional[ParsedTestCase]:
        """
        Parse a single test block into a ParsedTestCase.
        
        Returns None if block is invalid or empty.
        Raises ValueError if required fields are missing.
        """
        block = block.strip()
        if not block:
            return None

        # Extract the heading (we only consider `### ...` blocks)
        heading_match = re.match(self.HEADING_PATTERN, block, re.MULTILINE)
        if not heading_match:
            # Robustness: skip invalid blocks instead of crashing generation.
            logger.warning("Skipped block: no valid test heading found")
            return None

        test_name = heading_match.group(1).strip(':').strip()
        if not test_name:
            logger.warning("Skipped block: empty test heading")
            return None

        # Extract key-value pairs from the rest of the block.
        kvpairs = extract_key_value_pairs(block)
        # Normalize keys to lowercase for consistent mapping.
        kvpairs = {k.lower(): v for k, v in kvpairs.items()}
        logger.debug("Parsed kvpairs", test_name=test_name, kvpairs=kvpairs)

        # Field normalization:
        # - Support both `Endpoint` and `Target` as aliases for the HTTP endpoint string.
        if "endpoint" not in kvpairs and "target" in kvpairs:
            kvpairs["endpoint"] = kvpairs["target"]

        # Required field
        if "endpoint" not in kvpairs:
            logger.warning(
                "Skipped block: missing endpoint/target field",
                test_name=test_name,
                keys=list(kvpairs.keys()),
            )
            return None

        endpoint_str = kvpairs["endpoint"].strip("`").strip()
        logger.debug("Extracted endpoint", test_name=test_name, endpoint_str=endpoint_str)
        if not endpoint_str:
            logger.warning("Skipped block: endpoint is empty after cleaning", test_name=test_name)
            return None

        method, path = parse_endpoint(endpoint_str)

        # Parse optional input
        input_data = None
        if "input" in kvpairs:
            input_raw = kvpairs["input"]
            is_valid_json, parsed_input = extract_json_payload(input_raw)
            if is_valid_json:
                input_data = parsed_input
            else:
                # Fallback: parse non-JSON input like "username=admin password=pass".
                parsed_form = parse_form_data(input_raw)
                if parsed_form is not None:
                    input_data = parsed_form
                else:
                    logger.warning(
                        f"Could not parse input as JSON or form data: {str(input_raw)[:50]}",
                        test_name=test_name,
                    )

        # Parse expected status code
        expected_status = 200
        if "expected" in kvpairs:
            expected_status = extract_status_code(kvpairs["expected"])

        # Parse optional description
        description = kvpairs.get("description", None)

        # Create and validate model
        test_case = ParsedTestCase(
            name=test_name,
            endpoint=path,
            method=HTTPMethod[method],
            input_data=input_data,
            expected_status=expected_status,
            description=description,
        )

        return test_case


# ============================================================================
# Backward Compatibility Wrapper
# ============================================================================

class MarkdownTestParser:
    """
    Backward-compatible wrapper around MarkdownTestParserV2.
    
    Provides the same interface as the old parser but uses the new implementation.
    """
    
    def __init__(self):
        self.parser = MarkdownTestParserV2()
    
    def parse(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Parse markdown text and return list of test case dicts.
        
        This maintains backward compatibility with the old API.
        
        Args:
            markdown_text: Raw markdown content
            
        Returns:
            List of dicts with keys: name, endpoint, input, expected, description
        """
        spec = self.parser.parse(markdown_text)
        
        # Convert Pydantic models back to dicts for compatibility
        result = []
        for test_case in spec.test_cases:
            # Safely extract method value (could be string or enum)
            if isinstance(test_case.method, str):
                method_str = test_case.method
            elif hasattr(test_case.method, "value"):
                method_str = test_case.method.value
            else:
                method_str = str(test_case.method)
            
            result.append({
                "name": test_case.name,
                "endpoint": f"{method_str} {test_case.endpoint}",
                "input": str(test_case.input_data) if test_case.input_data else "{}",
                "expected": str(test_case.expected_status),
                "description": test_case.description,
            })
        
        return result
