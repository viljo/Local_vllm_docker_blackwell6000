# Quick Start: Tool Calling Implementation

**Feature**: 003-cline-tool-calling
**Branch**: `003-cline-tool-calling`
**Date**: 2025-11-12

## Overview

This guide provides a rapid implementation path for adding OpenAI-compatible tool calling support to the Local LLM Service router. Follow these steps to enable Cline and other AI coding assistants to interact with your local models.

---

## Prerequisites

- Python 3.11+
- FastAPI router running at `/home/asvil/git/local_llm_service/router/`
- vLLM backend(s) accessible
- Basic familiarity with Pydantic and FastAPI

---

## Implementation Steps

### Step 1: Update Pydantic Models (30 minutes)

**File**: `router/app/main.py` (lines 256-269)

**Changes**:
1. Import additional types
2. Update `ChatMessage` to support tool roles and fields
3. Add `Tool`, `ToolFunction` models
4. Update `ChatCompletionRequest` with tool parameters
5. Use `ConfigDict(extra='allow')` for forward compatibility

**Code**:
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Union

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra='allow')

    role: str  # system/user/assistant/tool
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ToolFunction(BaseModel):
    model_config = ConfigDict(extra='allow')

    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class Tool(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: str = "function"
    function: ToolFunction

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra='allow')

    model: str
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    stop: Optional[Union[str, List[str]]] = None

    # NEW: Tool calling
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None
    stream_options: Optional[Dict[str, Any]] = None
```

### Step 2: Create Transformation Module (1 hour)

**File**: `router/app/transformations.py` (new)

**Purpose**: Handle tool injection and extraction

**Code**:
```python
import json
import re
import secrets
import string
from typing import List, Optional, Dict, Any

def generate_tool_call_id() -> str:
    """Generate unique tool call ID"""
    alphabet = string.ascii_letters + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(24))
    return f"call_{suffix}"

def tools_to_system_prompt(tools: List) -> str:
    """Convert tools to system prompt instructions"""
    if not tools:
        return ""

    tool_descs = []
    for tool in tools:
        func = tool.function
        tool_descs.append(f"""
Function: {func.name}
Description: {func.description or 'No description'}
Parameters: {json.dumps(func.parameters.dict() if hasattr(func.parameters, 'dict') else func.parameters, indent=2)}
""")

    return f"""# Available Functions

To use a function, respond with:

```json
{{
  "tool_calls": [
    {{
      "id": "call_<random>",
      "type": "function",
      "function": {{
        "name": "<function_name>",
        "arguments": "<json_string>"
      }}
    }}
  ]
}}
```

Available functions:
{"".join(tool_descs)}

IMPORTANT: The "arguments" field must be a JSON string. Only use listed functions.
"""

def inject_tools_into_messages(messages: List, tools: Optional[List]) -> List:
    """Inject tool definitions into system message"""
    if not tools:
        return messages

    tool_prompt = tools_to_system_prompt(tools)
    modified = []
    has_system = False

    for msg in messages:
        if msg.role == "system" and not has_system:
            # Append to existing system message
            content = f"{msg.content}\n\n{tool_prompt}"
            modified.append(type(msg)(role="system", content=content))
            has_system = True
        else:
            modified.append(msg)

    if not has_system:
        # Prepend system message
        modified.insert(0, type(messages[0])(role="system", content=tool_prompt))

    return modified

def extract_tool_calls_from_text(content: str) -> Optional[List[Dict[str, Any]]]:
    """Extract tool_calls from model output"""
    if not content:
        return None

    # Pattern 1: JSON code block
    pattern = r'```json\s*(\{.*?\})\s*```'
    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        try:
            parsed = json.loads(match)
            if "tool_calls" in parsed:
                return parsed["tool_calls"]
        except json.JSONDecodeError:
            continue

    # Pattern 2: Direct JSON
    try:
        parsed = json.loads(content.strip())
        if isinstance(parsed, dict) and "tool_calls" in parsed:
            return parsed["tool_calls"]
    except json.JSONDecodeError:
        pass

    return None

def transform_response_with_tools(response: Dict[str, Any], request) -> Dict[str, Any]:
    """Inject tool_calls into backend response"""
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
        message["tool_calls"] = tool_calls
        if content.strip().startswith("{"):
            message["content"] = None
        choice["finish_reason"] = "tool_calls"
        modified["choices"][0] = choice

    return modified
```

### Step 3: Update Chat Completions Endpoint (1 hour)

**File**: `router/app/main.py` (lines 392-503)

**Changes**:
```python
from .transformations import (
    inject_tools_into_messages,
    transform_response_with_tools
)

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key)
):
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Request - model={request.model}, tools={len(request.tools or [])}")

    # Route to backend
    backend_url = get_backend_url(request.model)
    backend_endpoint = f"{backend_url}/v1/chat/completions"

    # Transform request: inject tools if needed
    messages = inject_tools_into_messages(request.messages, request.tools)

    # Prepare payload (filter tool params for backend)
    payload = request.model_dump(exclude_none=True)
    payload["messages"] = [msg.model_dump() for msg in messages]
    payload["model"] = MODEL_NAME_MAPPING.get(request.model, request.model)

    # Remove tool params (backend doesn't support them yet)
    payload.pop("tools", None)
    payload.pop("tool_choice", None)
    payload.pop("parallel_tool_calls", None)
    payload.pop("stream_options", None)

    try:
        if request.stream:
            # TODO: Implement streaming with tool detection
            # For now, forward as-is
            async def stream_generator():
                async with http_client.stream("POST", backend_endpoint, json=payload) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk.decode('utf-8')

            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            # Non-streaming: transform response
            response = await http_client.post(backend_endpoint, json=payload)

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.json())

            # Transform response to inject tool_calls
            backend_response = response.json()
            transformed = transform_response_with_tools(backend_response, request)

            logger.info(f"[{request_id}] Success")
            return transformed

    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}")
        raise
```

### Step 4: Test Basic Functionality (30 minutes)

**Create test file**: `test_tool_calling.py`

```python
import httpx
import json

BASE_URL = "http://localhost:8080/v1"
API_KEY = "sk-local-dev-key"

async def test_tool_calling():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": "gpt-oss-120b",
                "messages": [
                    {"role": "user", "content": "Read the file /tmp/test.txt"}
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "description": "Read a file",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"}
                                },
                                "required": ["path"]
                            }
                        }
                    }
                ]
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        # Check for tool_calls
        data = response.json()
        if "choices" in data:
            message = data["choices"][0]["message"]
            if "tool_calls" in message:
                print("\n✅ Tool calls detected!")
                print(f"Function: {message['tool_calls'][0]['function']['name']}")
            else:
                print("\n❌ No tool calls in response")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tool_calling())
```

**Run test**:
```bash
python test_tool_calling.py
```

---

## Testing with Cline

### 1. Configure Cline

In Cline settings (`.vscode/settings.json` or Cline extension):

```json
{
  "cline.apiProvider": "openai-compatible",
  "cline.openAiCompatible.baseUrl": "http://localhost:8080/v1",
  "cline.openAiCompatible.apiKey": "sk-local-dev-key",
  "cline.openAiCompatible.modelId": "gpt-oss-120b"
}
```

### 2. Test Commands

Try these commands in Cline:
1. "Read the file ./README.md"
2. "List all Python files in the current directory"
3. "Create a new file called test.txt with 'Hello World'"

### 3. Expected Behavior

- Cline sends requests with `tools` array
- Your API injects tools into system prompt
- Model responds with tool_calls JSON
- Your API transforms response to OpenAI format
- Cline executes tools locally
- Cline sends tool results back
- Model processes results and responds

---

## Troubleshooting

### Issue: 422 Validation Error

**Symptom**: `Extra inputs are not permitted: tools`

**Solution**: Ensure `ConfigDict(extra='allow')` is set on Pydantic models

### Issue: No Tool Calls Detected

**Symptom**: Model responds with text instead of tool_calls

**Solution**:
- Check if tools are properly injected into system prompt (add logging)
- Try a better model (GPT-OSS 120B or Qwen 2.5)
- Verify tool descriptions are clear

### Issue: Invalid JSON in arguments

**Symptom**: `json.JSONDecodeError` when parsing tool arguments

**Solution**:
- Model may not follow format exactly
- Add error handling in `extract_tool_calls_from_text()`
- Consider using stricter prompt instructions

---

## Next Steps

After basic functionality works:

1. **Add Streaming Support** (Phase 2)
   - Implement buffered streaming with tool detection
   - Add `stream_options.include_usage` support

2. **Enhance Error Handling** (Phase 2)
   - OpenAI-compatible error format
   - Detailed validation messages

3. **Add Tests** (Phase 3)
   - Unit tests for transformations
   - Integration tests with full workflow
   - Cline compatibility test suite

4. **Optimize Performance** (Phase 4)
   - Use `orjson` for faster JSON parsing
   - Compile regex patterns
   - Profile and optimize hot paths

---

## References

- **Feature Spec**: `specs/003-cline-tool-calling/spec.md`
- **Research**: `specs/003-cline-tool-calling/research.md`
- **Data Model**: `specs/003-cline-tool-calling/data-model.md`
- **API Contract**: `specs/003-cline-tool-calling/contracts/tool-calling-api.yaml`
- **Implementation Plan**: `specs/003-cline-tool-calling/plan.md`

---

**Estimated Time to MVP**: 2-3 hours
**Estimated Time to Production**: 5-8 days (including testing and optimization)

**Last Updated**: 2025-11-12
