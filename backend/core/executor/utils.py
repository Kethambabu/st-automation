"""
AI Test Platform — Test Execution Utilities

Helper functions for the test execution pipeline.
"""

import re
from typing import List
from utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_test_name(test_id: str, test_name: str) -> str:
    """
    Generate a safe Python function name from test ID and name.
    
    Args:
        test_id: UUID of the test case
        test_name: Human-readable test name
        
    Returns:
        Valid Python function name: test_<uuid_first_8>_<sanitized_name>
        
    Examples:
        >>> sanitize_test_name("abc123def456", "Valid Login")
        'test_abc123de_valid_login'
        
        >>> sanitize_test_name("xyz789", "User/Role Check-@Special!")
        'test_xyz789_user_role_check_special'
    """
    # Take first 8 chars of UUID
    uuid_short = test_id[:8] if test_id else "unknown"
    
    # Convert to lowercase and replace non-alphanumeric with underscore
    sanitized = re.sub(r'[^a-z0-9_]', '_', test_name.lower())
    
    # Remove leading/trailing underscores and collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    
    # Ensure it doesn't exceed Python identifier limits (keep it reasonable)
    sanitized = sanitized[:40]  # Limit to 40 chars + prefix
    
    # Construct final name
    result = f"test_{uuid_short}_{sanitized}"
    
    # If somehow invalid, return generic name
    if not is_valid_python_identifier(result):
        logger.warning(f"Generated test name '{result}' is invalid, using fallback")
        return f"test_{uuid_short}_case"
    
    return result


def is_valid_python_identifier(name: str) -> bool:
    """Check if a string is a valid Python identifier."""
    return name.isidentifier() and not name.startswith('_')


def parse_endpoint(endpoint_str: str) -> tuple[str, str]:
    """
    Parse endpoint string into (method, path).
    
    Args:
        endpoint_str: String like "GET /users" or just "/users"
        
    Returns:
        Tuple of (method, path)
        
    Examples:
        >>> parse_endpoint("GET /users/123")
        ('GET', '/users/123')
        
        >>> parse_endpoint("/api/health")
        ('GET', '/api/health')
        
        >>> parse_endpoint("POST /data")
        ('POST', '/data')
    """
    endpoint_str = endpoint_str.strip()
    
    # Check if it starts with HTTP method
    parts = endpoint_str.split(' ', 1)
    
    if len(parts) == 2:
        method_candidate, path = parts
        method_candidate = method_candidate.upper()
        
        valid_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
        if method_candidate in valid_methods:
            path = path.strip()
            if not path.startswith('/'):
                path = '/' + path
            return method_candidate, path
    
    # No method found, default to GET
    path = endpoint_str
    if not path.startswith('/'):
        path = '/' + path
    
    return "GET", path


def extract_status_code(status_str: str) -> int:
    """
    Extract HTTP status code from string.
    
    Args:
        status_str: String like "200", "200 OK", "401 Unauthorized"
        
    Returns:
        Integer status code
        
    Examples:
        >>> extract_status_code("200")
        200
        
        >>> extract_status_code("404 Not Found")
        404
        
        >>> extract_status_code("INVALID")
        200  # Defaults to 200
    """
    status_str = status_str.strip()
    
    # Try to extract first 3 digits
    match = re.search(r'\b(\d{3})\b', status_str)
    if match:
        try:
            code = int(match.group(1))
            if 100 <= code <= 599:
                return code
        except ValueError:
            pass
    
    logger.warning(f"Could not parse status code from '{status_str}', defaulting to 200")
    return 200


def extract_json_payload(input_str: str) -> tuple[bool, dict]:
    """
    Safely extract JSON payload from string.
    
    Args:
        input_str: String that may contain JSON
        
    Returns:
        Tuple of (is_valid_json, parsed_dict)
        
    Examples:
        >>> extract_json_payload('{"name": "John"}')
        (True, {"name": "John"})
        
        >>> extract_json_payload("hello world")
        (False, {})
    """
    import json
    import ast
    
    if not input_str or not input_str.strip():
        return True, {}
    
    input_str = input_str.strip()
    
    # Try JSON parsing first
    try:
        return True, json.loads(input_str)
    except json.JSONDecodeError:
        pass
    
    # Try Python dict literal evaluation
    try:
        result = ast.literal_eval(input_str)
        if isinstance(result, dict):
            return True, result
    except (ValueError, SyntaxError):
        pass

    # Try URL-encoded form/query string fallback.
    # Examples it should handle:
    #   - "a=1&b=2"
    #   - "username=admin password=pass" (spaces instead of &)
    try:
        from urllib.parse import parse_qs

        s_norm = input_str.strip()

        # If string looks like whitespace-separated key=value pairs,
        # normalize whitespace to '&' so parse_qs can parse it.
        if "&" not in s_norm and " " in s_norm and "=" in s_norm:
            s_norm = "&".join(s_norm.split())

        parsed = parse_qs(s_norm, keep_blank_values=True)
        if parsed:
            converted = {
                k: (v[0] if len(v) == 1 else v)
                for k, v in parsed.items()
            }
            return True, converted
    except Exception:
        pass
    
    logger.warning(f"Could not parse input as JSON: {input_str[:50]}")
    return False, {}


def split_into_blocks(text: str, block_marker: str = "###") -> List[str]:
    """
    Split text into logical blocks marked by a header marker.
    
    Args:
        text: Full text content
        block_marker: Marker for block start (e.g., "###")
        
    Returns:
        List of text blocks
        
    Examples:
        >>> blocks = split_into_blocks("### Test 1\\nContent\\n### Test 2\\nContent")
        >>> len(blocks)
        2
    """
    lines = text.split('\n')
    blocks = []
    current_block = []
    
    for line in lines:
        if line.strip().startswith(block_marker):
            if current_block:
                blocks.append('\n'.join(current_block).strip())
                current_block = []
            current_block.append(line)
        else:
            current_block.append(line)
    
    if current_block:
        blocks.append('\n'.join(current_block).strip())
    
    return [b for b in blocks if b]  # Filter empty blocks


def extract_key_value_pairs(text: str) -> dict[str, str]:
    """
    Extract key-value pairs from markdown text.
    
    Matches patterns like:
    - **Key**: value
    - *Key*: value
    - Key: value
    
    Returns dict of normalized key-value pairs.
    Handles malformed markdown gracefully.
    """
    pairs = {}
    
    if not text or not text.strip():
        return pairs
    
    # Pattern: **key**: value or *key*: value or key: value
    # This pattern captures optional asterisks, word characters, optional asterisks, colon, and value
    pattern = r'\*{0,2}(\w+)\*{0,2}\s*:\s*([^\n]+)'
    
    for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
        key = match.group(1).lower().strip()
        value = match.group(2).strip()
        
        # Skip if key is empty or value is empty
        if key and value:
            pairs[key] = value
    
    return pairs
