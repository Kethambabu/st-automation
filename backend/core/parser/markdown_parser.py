"""
AI Test Platform — Markdown Test Specification Parser

Converts human-readable Markdown test cases back into structured JSON data.
Handles both strict (AI-generated) patterns and simplified (user-edited) patterns.
"""

import re
from typing import List, Dict, Any

from utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownTestParser:
    """Parses Markdown text into structured JSON test cases."""
    
    def parse(self, markdown_text: str) -> List[Dict[str, Any]]:
        tests = []
        current_test = {}
        
        lines = markdown_text.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 1. Name/Title detection (e.g. "### Test Case 1:" or "### Valid Login Attempt")
            name_match = re.search(r'^###\s+(.+)', line)
            if name_match:
                # If we were tracking a previous test case and it has an endpoint, save it
                if current_test and "endpoint" in current_test:
                    tests.append(current_test)
                
                # Start a new test case
                current_test = {"name": name_match.group(1).strip(":")}
                
            # 2. Endpoint/Target detection
            elif re.search(r'^\*?\*?(Target|Endpoint)\*?\*?:', line, re.IGNORECASE):
                val = re.sub(r'^\*?\*?(Target|Endpoint)\*?\*?:\s*', '', line, flags=re.IGNORECASE)
                val = val.replace('`', '').strip()  # Remove backticks if present
                current_test["endpoint"] = val
                
            # 3. Input detection
            elif re.search(r'^\*?\*?Input\*?\*?:', line, re.IGNORECASE):
                val = re.sub(r'^\*?\*?Input\*?\*?:\s*', '', line, flags=re.IGNORECASE)
                val = val.replace('`', '').strip()
                current_test["input"] = val
                
            # 4. Expected detection
            elif re.search(r'^\*?\*?Expected\*?\*?:', line, re.IGNORECASE):
                val = re.sub(r'^\*?\*?Expected\*?\*?:\s*', '', line, flags=re.IGNORECASE)
                val = val.replace('`', '').strip()
                current_test["expected"] = val

        # Ensure the final test case in the loop is appended
        if current_test and "endpoint" in current_test:
            tests.append(current_test)
            
        logger.info(f"Parsed {len(tests)} test cases from markdown.")
        return tests
