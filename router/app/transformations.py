"""
Tool calling transformations for OpenAI-compatible API
Handles injection of tool definitions into prompts and extraction from responses
"""
import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def create_error_response(
    message: str,
    error_type: str = "invalid_request_error",
    code: Optional[str] = None,
    param: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create OpenAI-compatible error response.

    Args:
        message: Human-readable error message
        error_type: Error type (invalid_request_error, invalid_tool_schema, etc.)
        code: Optional error code
        param: Optional parameter name that caused the error

    Returns:
        Error response dictionary in OpenAI format
    """
    error_dict = {
        "error": {
            "message": message,
            "type": error_type
        }
    }

    if code:
        error_dict["error"]["code"] = code

    if param:
        error_dict["error"]["param"] = param

    return error_dict


def tools_to_system_prompt(tools: List) -> str:
    """
    Convert tool definitions to structured system prompt instructions.

    Args:
        tools: List of Tool objects with function definitions

    Returns:
        Formatted system prompt with tool instructions
    """
    if not tools:
        return ""

    tool_descs = []
    for tool in tools:
        func = tool.function
        # Handle both Pydantic models and dicts
        func_dict = func.model_dump() if hasattr(func, 'model_dump') else (
            func.dict() if hasattr(func, 'dict') else func
        )

        tool_descs.append(f"""
Function: {func_dict.get('name', 'unknown')}
Description: {func_dict.get('description', 'No description')}
Parameters: {json.dumps(func_dict.get('parameters', {}), indent=2)}
""")

    return f"""# Available Functions

You have access to the following functions. To use a function, respond with a JSON code block:

```json
{{
  "tool_calls": [
    {{
      "id": "call_<random_id>",
      "type": "function",
      "function": {{
        "name": "<function_name>",
        "arguments": "<json_string_of_arguments>"
      }}
    }}
  ]
}}
```

Available functions:
{"".join(tool_descs)}

IMPORTANT:
- Only use functions listed above
- The "arguments" field must be a JSON string, not a JSON object
- Generate a unique ID starting with "call_" for each tool call
- You can call multiple functions by adding them to the tool_calls array
"""


def inject_tools_into_messages(messages: List, tools: Optional[List]) -> List:
    """
    Inject tool definitions into the conversation messages.

    Appends tool instructions to existing system message or prepends a new one.

    Args:
        messages: List of ChatMessage objects
        tools: List of Tool objects or None

    Returns:
        Modified list of messages with tool instructions injected
    """
    if not tools:
        return messages

    tool_prompt = tools_to_system_prompt(tools)
    modified = []
    has_system = False

    for msg in messages:
        # Handle both Pydantic models and dicts
        msg_dict = msg.model_dump() if hasattr(msg, 'model_dump') else (
            msg.dict() if hasattr(msg, 'dict') else msg
        )

        if msg_dict.get('role') == "system" and not has_system:
            # Append to existing system message
            content = f"{msg_dict.get('content', '')}\n\n{tool_prompt}"
            modified.append({'role': 'system', 'content': content})
            has_system = True
        else:
            modified.append(msg_dict)

    if not has_system:
        # Prepend system message with tool instructions
        modified.insert(0, {'role': 'system', 'content': tool_prompt})

    return modified


def validate_tool_result_messages(messages: List[Dict[str, Any]]) -> None:
    """
    Validate that tool result messages have proper structure and reference valid tool calls.

    Args:
        messages: List of message dictionaries

    Raises:
        ValueError: If validation fails
    """
    # Collect all tool_call_ids from assistant messages
    valid_tool_call_ids = set()

    for msg in messages:
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            for tool_call in msg['tool_calls']:
                valid_tool_call_ids.add(tool_call.get('id'))

    # Validate tool messages
    for msg in messages:
        if msg.get('role') == 'tool':
            tool_call_id = msg.get('tool_call_id')
            if not tool_call_id:
                raise ValueError("Tool message missing required field: tool_call_id")

            if tool_call_id not in valid_tool_call_ids:
                raise ValueError(
                    f"Tool message references unknown tool_call_id: {tool_call_id}. "
                    f"Valid IDs: {valid_tool_call_ids}"
                )

            if not msg.get('content'):
                raise ValueError("Tool message missing required field: content")


def transform_response_with_tools(
    response: Dict[str, Any],
    request
) -> Dict[str, Any]:
    """
    Transform backend response to inject tool_calls if detected in content.

    Args:
        response: Backend response dictionary
        request: Original request object with tools

    Returns:
        Modified response with tool_calls injected if applicable
    """
    # Import here to avoid circular dependency
    from .tool_parsing import extract_tool_calls_from_text

    if not request.tools:
        return response

    modified = response.copy()

    if "choices" not in modified or not modified["choices"]:
        return modified

    choice = modified["choices"][0]
    message = choice.get("message", {})
    content = message.get("content", "")

    tool_calls = extract_tool_calls_from_text(content)

    if tool_calls:
        logger.info(f"Detected {len(tool_calls)} tool call(s) in response")
        message["tool_calls"] = tool_calls

        # If the entire content is JSON, set content to null
        stripped_content = content.strip()
        if stripped_content.startswith("{") or stripped_content.startswith("```json"):
            message["content"] = None

        choice["finish_reason"] = "tool_calls"
        choice["message"] = message
        modified["choices"][0] = choice

    return modified


def transform_request_for_backend(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove unsupported tool-related parameters before forwarding to backend.

    Args:
        request_dict: Request dictionary

    Returns:
        Filtered request dictionary safe for backend
    """
    # Parameters that should be filtered out
    unsupported_params = [
        'tools',
        'tool_choice',
        'parallel_tool_calls',
        'stream_options',
        'reasoning_effort'  # Future parameter
    ]

    # Track which parameters were filtered
    filtered_out = []
    filtered = {}

    for k, v in request_dict.items():
        if k in unsupported_params:
            filtered_out.append(k)
        else:
            filtered[k] = v

    if filtered_out:
        logger.info(f"Filtered out unsupported parameters for backend: {', '.join(filtered_out)}")

    return filtered
