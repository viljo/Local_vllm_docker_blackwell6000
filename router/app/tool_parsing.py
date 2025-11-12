"""
Tool call detection and parsing from model responses
Supports multiple patterns: JSON code blocks, XML-style tags, and direct JSON
"""
import json
import re
import secrets
import string
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def generate_tool_call_id() -> str:
    """
    Generate unique tool call ID in OpenAI format.

    Returns:
        ID string in format: call_<24_random_chars>
    """
    alphabet = string.ascii_letters + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(24))
    return f"call_{suffix}"


def extract_tool_calls_from_text(content: str) -> Optional[List[Dict[str, Any]]]:
    """
    Extract tool_calls from model output text.

    Supports multiple patterns:
    1. JSON code block: ```json\n{...}\n```
    2. Direct JSON object: {...}
    3. XML-style tags: <tool_call>...</tool_call>

    Args:
        content: Model output text

    Returns:
        List of tool call dictionaries or None if no tool calls detected
    """
    if not content:
        return None

    # Pattern 1: JSON code block with tool_calls
    json_block_pattern = r'```json\s*(\{.*?\})\s*```'
    matches = re.findall(json_block_pattern, content, re.DOTALL)

    for match in matches:
        try:
            parsed = json.loads(match)
            if "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
                tool_calls = parsed["tool_calls"]
                # Validate and normalize tool calls
                normalized = []
                for tc in tool_calls:
                    if validate_tool_call_structure(tc):
                        # Ensure ID exists
                        if not tc.get('id'):
                            tc['id'] = generate_tool_call_id()
                        normalized.append(tc)

                if normalized:
                    logger.debug(f"Extracted {len(normalized)} tool call(s) from JSON code block")
                    return normalized
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse JSON code block: {e}")
            continue

    # Pattern 2: Direct JSON object
    try:
        parsed = json.loads(content.strip())
        if isinstance(parsed, dict) and "tool_calls" in parsed:
            tool_calls = parsed["tool_calls"]
            if isinstance(tool_calls, list):
                normalized = []
                for tc in tool_calls:
                    if validate_tool_call_structure(tc):
                        if not tc.get('id'):
                            tc['id'] = generate_tool_call_id()
                        normalized.append(tc)

                if normalized:
                    logger.debug(f"Extracted {len(normalized)} tool call(s) from direct JSON")
                    return normalized
    except json.JSONDecodeError:
        pass

    # Pattern 3: XML-style tool call tags
    xml_pattern = r'<tool_call>(.*?)</tool_call>'
    xml_matches = re.findall(xml_pattern, content, re.DOTALL)

    if xml_matches:
        tool_calls = []
        for xml_content in xml_matches:
            try:
                parsed = json.loads(xml_content.strip())
                if validate_tool_call_structure(parsed):
                    if not parsed.get('id'):
                        parsed['id'] = generate_tool_call_id()
                    tool_calls.append(parsed)
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse XML-style tool call content")
                continue

        if tool_calls:
            logger.debug(f"Extracted {len(tool_calls)} tool call(s) from XML tags")
            return tool_calls

    # Pattern 4: Multiple separate JSON objects (for parallel calls)
    # Look for multiple {"type": "function", "function": {...}} patterns
    function_call_pattern = r'\{[^{}]*"type"\s*:\s*"function"[^{}]*"function"\s*:\s*\{[^{}]*\}[^{}]*\}'
    function_matches = re.findall(function_call_pattern, content, re.DOTALL)

    if len(function_matches) > 0:
        tool_calls = []
        for match in function_matches:
            try:
                # Wrap in tool_calls array format if needed
                parsed = json.loads(match)
                if validate_tool_call_structure(parsed):
                    if not parsed.get('id'):
                        parsed['id'] = generate_tool_call_id()
                    tool_calls.append(parsed)
            except json.JSONDecodeError:
                continue

        if tool_calls:
            logger.debug(f"Extracted {len(tool_calls)} tool call(s) from function pattern")
            return tool_calls

    return None


def validate_tool_call_structure(tool_call: Dict[str, Any]) -> bool:
    """
    Validate that a tool call has the required structure.

    Required fields:
    - type: must be "function"
    - function: must be a dict with "name" and "arguments"

    Args:
        tool_call: Tool call dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(tool_call, dict):
        return False

    # Check type field
    if tool_call.get('type') != 'function':
        logger.debug(f"Invalid tool call: type must be 'function', got {tool_call.get('type')}")
        return False

    # Check function field
    function = tool_call.get('function')
    if not isinstance(function, dict):
        logger.debug("Invalid tool call: function must be a dict")
        return False

    # Check required function fields
    if 'name' not in function:
        logger.debug("Invalid tool call: function.name is required")
        return False

    if 'arguments' not in function:
        logger.debug("Invalid tool call: function.arguments is required")
        return False

    # Validate arguments is a string (JSON string)
    if not isinstance(function['arguments'], str):
        logger.debug(f"Invalid tool call: arguments must be a string, got {type(function['arguments'])}")
        return False

    # Try to parse arguments as JSON to ensure it's valid
    try:
        json.loads(function['arguments'])
    except json.JSONDecodeError:
        logger.debug(f"Invalid tool call: arguments is not valid JSON: {function['arguments']}")
        return False

    return True


def validate_tool_exists(tool_call: Dict[str, Any], tools: List) -> bool:
    """
    Validate that a tool call references a function that exists in the tools array.

    Args:
        tool_call: Tool call dictionary
        tools: List of Tool objects from request

    Returns:
        True if tool exists, False otherwise
    """
    if not tools:
        return False

    function_name = tool_call.get('function', {}).get('name')
    if not function_name:
        return False

    # Extract function names from tools
    tool_names = []
    for tool in tools:
        # Handle both Pydantic models and dicts
        if hasattr(tool, 'function'):
            func = tool.function
            if hasattr(func, 'name'):
                tool_names.append(func.name)
            elif isinstance(func, dict):
                tool_names.append(func.get('name'))
        elif isinstance(tool, dict):
            func = tool.get('function', {})
            tool_names.append(func.get('name'))

    return function_name in tool_names


def detect_multiple_tool_calls(content: str) -> int:
    """
    Count potential tool calls in content for parallel execution detection.

    Args:
        content: Model output text

    Returns:
        Number of potential tool calls detected
    """
    tool_calls = extract_tool_calls_from_text(content)
    return len(tool_calls) if tool_calls else 0
