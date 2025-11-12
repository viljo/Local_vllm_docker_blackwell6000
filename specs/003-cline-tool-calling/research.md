# Research: OpenAI-Compatible Tool Calling Implementation

**Feature**: 003-cline-tool-calling
**Date**: 2025-11-12
**Status**: Complete

## Executive Summary

After comprehensive research into vLLM capabilities, OpenAI API specifications, and FastAPI middleware patterns, we recommend implementing tool calling support via a **prompt-engineering approach with response transformation** rather than relying on vLLM's native tool support. This approach provides maximum compatibility across all models and avoids known vLLM streaming bugs.

---

## 1. vLLM Native Tool Support Analysis

### Current Status

**vLLM HAS native tool calling support** (v0.6.0+, mature in v0.11.0+), but with significant limitations:

#### Supported Features
- `tools`, `tool_choice`, `parallel_tool_calls` parameters accepted
- Dedicated tool parsers for specific models (Llama 4, Hermes, Mistral, Qwen, etc.)
- OpenAI-compatible response format with `tool_calls` array
- Requires `--enable-auto-tool-choice` and `--tool-call-parser` flags

#### Critical Limitations
1. **Streaming Mode Bugs**:
   - Inconsistent tool call parsing in streaming
   - Missing `arguments` in streamed chunks
   - Missing `finish_reason` and `type` fields
   - Active GitHub issues as of 2025

2. **Model-Specific Requirements**:
   - Each model needs specific parser configuration
   - DeepSeek models have known tool calling issues
   - GGUF-converted models fail with tool calling errors
   - Parser performance can be bottleneck for long outputs

3. **Configuration Complexity**:
   - Must match model, chat template, and parser correctly
   - No automatic parser detection
   - Mismatches cause parsing failures without graceful degradation

### Decision: Prompt Engineering Approach

**Rationale**:
- ✅ Works with ANY model (no special training required)
- ✅ Avoids vLLM streaming bugs
- ✅ No backend reconfiguration needed
- ✅ Full control over tool call detection logic
- ✅ Can implement progressive enhancement (try native, fallback to prompt engineering)
- ⚠️ Slightly higher token usage (tools in prompt)
- ⚠️ Relies on model's ability to follow JSON formatting instructions

**Implementation Strategy**:
1. Inject tool definitions into system prompt
2. Instruct model to output JSON with `tool_calls` structure
3. Parse model response for tool call JSON blocks
4. Transform response to match OpenAI format

---

## 2. OpenAI API Specification

### Complete Tool Calling Flow

#### Request Structure
```json
{
  "model": "gpt-oss-120b",
  "messages": [{"role": "user", "content": "Read /tmp/test.txt"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read contents of a file",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {"type": "string", "description": "File path"}
          },
          "required": ["path"],
          "additionalProperties": false
        }
      }
    }
  ],
  "tool_choice": "auto",
  "parallel_tool_calls": true
}
```

#### Response Structure
```json
{
  "id": "chatcmpl-abc123",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc123xyz",
        "type": "function",
        "function": {
          "name": "read_file",
          "arguments": "{\"path\":\"/tmp/test.txt\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }],
  "usage": {"prompt_tokens": 82, "completion_tokens": 17, "total_tokens": 99}
}
```

#### Multi-Turn with Tool Results
```json
{
  "messages": [
    {"role": "user", "content": "Read /tmp/test.txt"},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {"name": "read_file", "arguments": "{\"path\":\"/tmp/test.txt\"}"}
      }]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "name": "read_file",
      "content": "File contents here..."
    }
  ]
}
```

### Key Validation Rules

1. **Tool Call ID Format**: Must start with `"call_"` followed by alphanumeric string
2. **Content Optionality**: `content` can be `null` when `tool_calls` present
3. **Role Values**: Must support `"system"`, `"user"`, `"assistant"`, and `"tool"`
4. **Finish Reason**: Set to `"tool_calls"` (not `"stop"`) when functions invoked
5. **Tool Results**: Must include `tool_call_id` matching previous tool call
6. **Message Order**: Tool results must immediately follow assistant message with tool calls

### Tool Choice Parameter Values

| Value | Behavior |
|-------|----------|
| `"auto"` | Model decides whether to call functions |
| `"none"` | Forces text response, no function calls |
| `"required"` | Forces at least one function call |
| `{"type": "function", "function": {"name": "X"}}` | Forces specific function call |

### Error Handling

**OpenAI Error Format**:
```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "invalid_request_error",
    "param": "parameter_name",
    "code": "error_code"
  }
}
```

**Common Error Types**:
- `invalid_request_error` - Malformed request or invalid parameters
- `invalid_tool_schema` - Tool definition JSON schema invalid
- `invalid_tool_call_id` - Tool result references non-existent tool call
- `invalid_message_order` - Tool message without preceding tool_calls

---

## 3. FastAPI Middleware Patterns

### Request Transformation

#### Flexible Pydantic Models (Pydantic v2)

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any, Union

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra='allow')

    role: str  # Allow any role: system/user/assistant/tool
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class Tool(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: str = "function"
    function: Dict[str, Any]  # Tool function definition

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra='allow')  # Accept unknown fields

    model: str
    messages: List[ChatMessage]
    stream: bool = False

    # Standard parameters
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    stop: Optional[Union[str, List[str]]] = None

    # Tool calling (NEW)
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None

    # Streaming options (NEW)
    stream_options: Optional[Dict[str, Any]] = None
```

**Benefits**:
- ✅ Backward compatible with existing clients
- ✅ Forward compatible with new OpenAI parameters
- ✅ Validation for known fields, graceful acceptance of unknown fields
- ✅ Type hints for IDE support

#### Tool Injection into System Prompt

```python
def tools_to_system_prompt(tools: List[Tool]) -> str:
    """Convert tool definitions to structured system prompt"""
    if not tools:
        return ""

    tool_descriptions = []
    for tool in tools:
        func = tool.function
        tool_descriptions.append(f"""
Function: {func['name']}
Description: {func.get('description', 'No description')}
Parameters: {json.dumps(func['parameters'], indent=2)}
""")

    return f"""# Available Functions

You have access to the following functions. To use a function, respond with:

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
{"".join(tool_descriptions)}

IMPORTANT: Only use listed functions. The "arguments" field must be a JSON string.
"""
```

### Response Transformation

#### Extract Tool Calls from Text

```python
import re
import json

def extract_tool_calls_from_text(content: str) -> Optional[List[Dict]]:
    """Parse model output to detect tool_calls"""
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
```

#### Transform Backend Response

```python
def transform_response_with_tools(
    backend_response: Dict[str, Any],
    request: ChatCompletionRequest
) -> Dict[str, Any]:
    """Inject tool_calls into response if detected"""
    if not request.tools:
        return backend_response

    response = backend_response.copy()
    choice = response["choices"][0]
    message = choice.get("message", {})
    content = message.get("content", "")

    tool_calls = extract_tool_calls_from_text(content)

    if tool_calls:
        message["tool_calls"] = tool_calls
        if content.strip().startswith("{"):
            message["content"] = None
        choice["finish_reason"] = "tool_calls"
        response["choices"][0] = choice

    return response
```

### Streaming Enhancement

#### Buffered Streaming for Tool Detection

```python
async def stream_with_tool_detection(
    backend_stream: AsyncIterator[bytes],
    request: ChatCompletionRequest
) -> AsyncIterator[str]:
    """Buffer stream to detect tools, then stream with modifications"""
    chunks = []
    full_content = ""

    # Collect all chunks
    async for chunk_bytes in backend_stream:
        chunk_str = chunk_bytes.decode('utf-8')
        chunks.append(chunk_str)

        if chunk_str.startswith('data: '):
            try:
                json_str = chunk_str[6:].strip()
                chunk_data = json.loads(json_str)
                delta = chunk_data["choices"][0].get("delta", {})
                full_content += delta.get("content", "")
            except:
                pass

    # Detect tool calls
    tool_calls = extract_tool_calls_from_text(full_content) if request.tools else None

    # Stream with modifications
    for chunk_str in chunks:
        if tool_calls and chunk_str.startswith('data: '):
            try:
                chunk_data = json.loads(chunk_str[6:].strip())
                if chunk_data["choices"][0].get("finish_reason"):
                    chunk_data["choices"][0]["delta"]["tool_calls"] = tool_calls
                    chunk_data["choices"][0]["finish_reason"] = "tool_calls"
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    continue
            except:
                pass

        yield chunk_str
```

### Performance Optimization

**Connection Pooling** (already implemented):
```python
http_client = httpx.AsyncClient(
    timeout=300.0,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    )
)
```

**Expected Overhead**:
- Request transformation: 2-5ms (tool injection)
- Response transformation: 3-8ms (tool extraction)
- Streaming with buffering: 50-200ms (depends on response length)
- **Total**: < 200ms (meets SC-003 requirement)

---

## 4. Implementation Approach

### Recommended Architecture

**Intelligent Proxy Pattern**:
```
Cline → Router API → Transform Request → vLLM → Transform Response → Cline
         |            |                    |       |
         |            | • Inject tools     |       | • Extract tool_calls
         |            | • Filter params    |       | • Set finish_reason
         |            | • Add to prompt    |       | • Inject usage stats
```

**Key Components**:

1. **Request Pipeline**:
   - Validate tool definitions
   - Inject tools into system prompt (if not supported natively)
   - Filter unsupported parameters for backend
   - Track request context

2. **Response Pipeline**:
   - Parse backend response for tool calls
   - Transform to OpenAI format
   - Add usage statistics if requested
   - Handle errors gracefully

3. **Streaming Pipeline**:
   - Buffer chunks for tool detection
   - Modify chunks with tool_calls
   - Inject usage in final chunk

### Code Organization

```
router/app/
├── main.py (existing - modify endpoints)
├── models.py (NEW - Pydantic models)
├── transformations.py (NEW - request/response transforms)
├── tool_parsing.py (NEW - tool call extraction)
└── streaming.py (NEW - streaming handlers)
```

### Integration Points

**Current Endpoint** (`/home/asvil/git/local_llm_service/router/app/main.py:392-503`):
```python
@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,  # Now flexible
    raw_request: Request,
    api_key: str = Depends(verify_api_key)
):
    # NEW: Transform request
    payload = transform_request(request)

    # EXISTING: Route to backend
    backend_url = get_backend_url(request.model)

    if request.stream:
        # NEW: Enhanced streaming
        return StreamingResponse(
            stream_with_tool_detection(...),
            media_type="text/event-stream"
        )
    else:
        # EXISTING: Forward to backend
        response = await http_client.post(backend_endpoint, json=payload)

        # NEW: Transform response
        return transform_response_with_tools(response.json(), request)
```

---

## 5. Testing Strategy

### Unit Tests

```python
def test_tool_injection():
    """Test tools are correctly injected into system prompt"""
    tools = [Tool(type="function", function={"name": "read_file", "parameters": {}})]
    prompt = tools_to_system_prompt(tools)
    assert "read_file" in prompt
    assert "tool_calls" in prompt

def test_tool_extraction():
    """Test tool calls extracted from JSON response"""
    content = '```json\n{"tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]}\n```'
    tool_calls = extract_tool_calls_from_text(content)
    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "read_file"

def test_response_transformation():
    """Test backend response transformed to OpenAI format"""
    backend_response = {
        "choices": [{
            "message": {"role": "assistant", "content": '{"tool_calls": [...]}'},
            "finish_reason": "stop"
        }]
    }
    request = ChatCompletionRequest(model="test", messages=[], tools=[...])

    transformed = transform_response_with_tools(backend_response, request)
    assert transformed["choices"][0]["message"]["tool_calls"] is not None
    assert transformed["choices"][0]["finish_reason"] == "tool_calls"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_cline_compatibility():
    """Test full tool calling flow with Cline-like request"""
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-test-key"},
        json={
            "model": "gpt-oss-120b",
            "messages": [{"role": "user", "content": "Read /tmp/test.txt"}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "read_file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                }
            }],
            "tool_choice": "auto"
        }
    )

    assert response.status_code == 200
    data = response.json()
    message = data["choices"][0]["message"]

    # Should have tool_calls OR content (model decides)
    assert "tool_calls" in message or "content" in message
    if "tool_calls" in message:
        assert data["choices"][0]["finish_reason"] == "tool_calls"
```

---

## 6. Alternative Approaches Considered

### Alternative 1: Native vLLM Tool Support

**Pros**:
- Less code to maintain
- Leverages vLLM's built-in parsers
- No prompt token overhead

**Cons**:
- ❌ Known streaming bugs (dealbreaker)
- ❌ Requires model-specific configuration
- ❌ DeepSeek models have issues
- ❌ No fallback if parsing fails
- ❌ Backend reconfiguration needed

**Verdict**: Rejected due to streaming bugs and model compatibility issues

### Alternative 2: Hybrid Approach

**Strategy**: Try native support first, fallback to prompt engineering

**Pros**:
- Best of both worlds
- Progressive enhancement

**Cons**:
- Increased complexity
- Harder to debug
- Need capability detection
- Two code paths to maintain

**Verdict**: Defer to Phase 2 (P2 priority)

### Alternative 3: Client-Side Tool Handling

**Strategy**: Have Cline handle tool calling entirely

**Pros**:
- No backend changes

**Cons**:
- ❌ Breaks OpenAI API compatibility
- ❌ Defeats purpose of the feature
- ❌ Not acceptable for Cline

**Verdict**: Rejected - violates requirements

---

## 7. Implementation Roadmap

### Phase 0: Research (COMPLETE)
- [x] Investigate vLLM tool support
- [x] Document OpenAI API specification
- [x] Research FastAPI middleware patterns
- [x] Evaluate implementation approaches
- [x] Make architectural decisions

### Phase 1: Core Implementation (P0 - Critical)
Estimated: 2-3 days

1. **Update Pydantic Models** (4 hours)
   - Add tool-related fields to `ChatMessage`
   - Add `tools`, `tool_choice`, `parallel_tool_calls` to `ChatCompletionRequest`
   - Use `ConfigDict(extra='allow')` for flexibility

2. **Implement Request Transformation** (6 hours)
   - Create `transformations.py` module
   - Implement `tools_to_system_prompt()`
   - Implement `inject_tools_into_messages()`
   - Add request validation

3. **Implement Response Transformation** (6 hours)
   - Create `tool_parsing.py` module
   - Implement `extract_tool_calls_from_text()`
   - Implement `transform_response_with_tools()`
   - Handle edge cases (malformed JSON, no tools detected)

4. **Modify Chat Completions Endpoint** (4 hours)
   - Update `/v1/chat/completions` to use transformations
   - Add error handling
   - Test non-streaming flow

### Phase 2: Streaming Support (P1 - Important)
Estimated: 1-2 days

1. **Implement Streaming Handler** (6 hours)
   - Create `streaming.py` module
   - Implement `stream_with_tool_detection()`
   - Buffer and transform chunks

2. **Add Stream Options** (2 hours)
   - Support `stream_options.include_usage`
   - Inject usage stats in final chunk
   - Approximate token counts

### Phase 3: Testing & Validation (P1 - Important)
Estimated: 1-2 days

1. **Unit Tests** (4 hours)
   - Test tool injection
   - Test tool extraction
   - Test response transformation
   - Test error handling

2. **Integration Tests** (4 hours)
   - Full end-to-end tests
   - Cline compatibility tests
   - Multi-turn conversation tests
   - Streaming tests

3. **Manual Testing with Cline** (4 hours)
   - Connect Cline to local API
   - Test file operations
   - Test multi-turn workflows
   - Test parallel tool calls

### Phase 4: Optimization (P2 - Enhancement)
Estimated: 1 day

1. **Performance Optimization** (4 hours)
   - Use `orjson` for faster JSON parsing
   - Compile regex patterns
   - Profile and optimize hot paths

2. **Error Handling Enhancement** (2 hours)
   - Better OpenAI-compatible error messages
   - Detailed logging
   - Retry logic

### Total Estimated Time: 5-8 days

---

## 8. Success Criteria Mapping

| Success Criterion | Implementation Strategy |
|-------------------|------------------------|
| SC-001: File operations work without errors | Tool calling implemented with proper error handling |
| SC-002: Multi-turn conversations | Full conversation context supported in message history |
| SC-003: < 200ms overhead | Optimized transformation pipeline, minimal buffering |
| SC-004: 100% request acceptance | Flexible Pydantic models with `extra='allow'` |
| SC-005: 40% faster parallel execution | `parallel_tool_calls` parameter supported |
| SC-006: < 1% usage variance | Accurate token counting with tiktoken |
| SC-007: Clear error messages | OpenAI-compatible error format |
| SC-008: 20 sequential tool calls | No artificial limits on conversation length |
| SC-009: 95% malformed input detection | JSON schema validation on tool arguments |
| SC-010: Backward compatibility | Existing non-tool requests unaffected |

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Model doesn't follow JSON format | High | Medium | Use well-trained models (GPT-OSS, Qwen); fallback to text response |
| Streaming latency increases | Medium | High | Acceptable trade-off for tool support; optimize buffering |
| Tool call parsing false positives | Medium | Low | Strict regex patterns; validate tool exists in tools array |
| Backend timeout on long prompts | Medium | Low | Existing 300s timeout should suffice; monitor token counts |
| vLLM changes break passthrough | Low | Low | Minimal risk since we're not relying on vLLM tool support |

---

## 10. Open Questions & Decisions

### Resolved

✅ **Use vLLM native tool support?**
**Decision**: No, use prompt engineering. Avoids streaming bugs and works with all models.

✅ **Support streaming with tools?**
**Decision**: Yes, with buffering approach. Slight latency trade-off acceptable.

✅ **How to handle unsupported parameters?**
**Decision**: Use `ConfigDict(extra='allow')` to accept gracefully.

✅ **State management approach?**
**Decision**: Stateless proxy. Cline sends full context; no server-side state needed.

### Deferred to Implementation

⏸️ **Exact token counting for usage stats**
**Current**: Use tiktoken approximation
**Future**: May need model-specific tokenizers

⏸️ **Hybrid native/prompt approach**
**Current**: Pure prompt engineering
**Future P2**: Add native support detection and fallback

⏸️ **Tool call loop detection**
**Current**: No limits
**Future**: Add configurable max tool calls per conversation

---

## 11. References

### Official Documentation
- vLLM Tool Calling: https://docs.vllm.ai/en/stable/features/tool_calling.html
- OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic v2: https://docs.pydantic.dev/latest/

### Community Resources
- Berkeley Function Calling Leaderboard: https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html
- vLLM GitHub Issues (streaming bugs): https://github.com/vllm-project/vllm/issues/9693

### Project Files
- Feature Spec: `/home/asvil/git/local_llm_service/specs/003-cline-tool-calling/spec.md`
- Cline Requirements: `/home/asvil/git/local_llm_service/openai_api_requirements_for_cline.md`
- Current Router: `/home/asvil/git/local_llm_service/router/app/main.py`
- Test Suite: `/home/asvil/git/local_llm_service/test_api_complete.py`

---

## 12. Next Steps

1. ✅ **Complete research** (this document)
2. **Create data model** (Phase 1 design) → `data-model.md`
3. **Define API contracts** (Phase 1 design) → `contracts/tool-calling.yaml`
4. **Write quickstart guide** (Phase 1 design) → `quickstart.md`
5. **Update agent context** → `CLAUDE.md`
6. **Generate task breakdown** → `/speckit.tasks`

---

**Research Complete**: 2025-11-12
**Decision**: Implement tool calling via prompt engineering with response transformation
**Next Phase**: Design artifacts (data model, contracts, quickstart)
