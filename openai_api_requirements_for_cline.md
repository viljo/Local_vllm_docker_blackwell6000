# OpenAI API Implementation Requirements for Cline Compatibility

**Date:** 2025-11-12
**Context:** vLLM compatibility with Cline AI coding assistant
**vLLM Endpoint:** http://172.30.0.54:8080/v1
**Model:** gpt-oss-120b (120B parameters)

---

## Executive Summary

Cline requires specific OpenAI API parameters that are not currently supported by vLLM, causing 422 errors. This document specifies the complete set of OpenAI API functionality needed for full Cline compatibility.

---

## 1. Core Requirements (CRITICAL)

### 1.1 Chat Completions Endpoint: `/v1/chat/completions`

**Status:** ✅ Partially Implemented
**Priority:** P0 - Blocking

#### Required Request Parameters

| Parameter | Type | Status | Notes |
|-----------|------|--------|-------|
| `model` | string | ✅ Supported | Working |
| `messages` | array | ✅ Supported | Working |
| `temperature` | float | ✅ Supported | Working |
| `max_tokens` | integer | ✅ Supported | Working |
| `stream` | boolean | ✅ Supported | Working |
| `tools` | array | ⚠️ Partial | Tool calling support needed |
| `tool_choice` | string/object | ❌ Missing | Required for agentic workflows |
| `parallel_tool_calls` | boolean | ❌ Missing | Cline sets to `true` |
| `stream_options` | object | ❌ Missing | Cline uses `{include_usage: true}` |
| `reasoning_effort` | string | ❌ Missing | Extended thinking feature |
| `top_p` | float | ⚠️ Unknown | Likely supported |
| `presence_penalty` | float | ⚠️ Unknown | May be supported |
| `frequency_penalty` | float | ⚠️ Unknown | May be supported |
| `stop` | string/array | ⚠️ Unknown | May be supported |

#### Required Response Format

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-oss-120b",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "response text",
      "tool_calls": []  // ❌ Required for tool usage
    },
    "finish_reason": "stop",
    "logprobs": null
  }],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

**Current vLLM Response:** ✅ Mostly compatible, missing `tool_calls` structure

---

## 2. Tool/Function Calling (CRITICAL FOR CLINE)

**Status:** ❌ Not Implemented
**Priority:** P0 - Blocking for full functionality

### 2.1 Tool Definition Format

Cline sends tools in OpenAI's function calling format:

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read contents of a file",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "File path"
            }
          },
          "required": ["path"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### 2.2 Required Tool Parameters

| Parameter | Type | Description | Current Support |
|-----------|------|-------------|-----------------|
| `tools` | array | List of available tools | ❌ Rejected (422) |
| `tool_choice` | string/object | "auto", "none", or specific tool | ❌ Not supported |
| `parallel_tool_calls` | boolean | Allow multiple simultaneous tool calls | ❌ Not supported |

### 2.3 Expected Tool Call Response

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_xxx",
          "type": "function",
          "function": {
            "name": "read_file",
            "arguments": "{\"path\":\"/foo/bar.txt\"}"
          }
        }
      ]
    },
    "finish_reason": "tool_calls"
  }]
}
```

**Implementation Impact:** Without this, Cline cannot:
- Read/write files
- Execute bash commands
- Use browser automation
- Access MCP servers
- Perform any agentic actions

**Recommendation:** This is the #1 priority for full Cline compatibility.

---

## 3. Streaming with Usage Statistics

**Status:** ❌ Not Implemented
**Priority:** P1 - Important for UX

### 3.1 Stream Options

```json
{
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}
```

### 3.2 Expected Behavior

When `stream_options.include_usage` is `true`, the final streaming chunk should include usage statistics:

```
data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150}}

data: [DONE]
```

**Current vLLM Behavior:** Rejects request with 422 when `stream_options` is present

**Implementation Impact:** Cline can't display token usage in real-time

**Workaround:** Proxy strips this parameter (current solution)

---

## 4. Extended Thinking/Reasoning

**Status:** ❌ Not Implemented
**Priority:** P2 - Nice to have

### 4.1 Reasoning Effort Parameter

```json
{
  "reasoning_effort": "medium"  // or "low", "high"
}
```

### 4.2 Expected Response

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "final response",
      "reasoning_content": "thinking process..."
    }
  }]
}
```

**Current vLLM Behavior:** Rejects with 422

**Implementation Impact:** Limited - Cline can work without this

**Recommendation:** Low priority, but valuable for complex reasoning tasks

---

## 5. Models Endpoint: `/v1/models`

**Status:** ✅ Implemented
**Priority:** P0 - Required

### Current Implementation
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-oss-120b",
      "object": "model",
      "created": 1762937994,
      "owned_by": "vllm",
      "status": "ready"
    }
  ]
}
```

**Assessment:** ✅ Fully compatible with Cline

---

## 6. Error Handling

**Status:** ⚠️ Partially Implemented
**Priority:** P1 - Important

### 6.1 Current Issues

| Scenario | Expected | Actual | Impact |
|----------|----------|--------|--------|
| Unsupported parameter | Ignore or error message | HTTP 422 with no body | Poor debugging |
| Invalid API key | `{"error": {"message": "Invalid API key"}}` | Working ✅ | Good |
| Model not found | `{"error": {"type": "invalid_request_error"}}` | Unknown | - |
| Rate limiting | HTTP 429 with retry-after | Unknown | - |

### 6.2 Recommendations

1. **422 Errors:** Include detailed error message in response body:
```json
{
  "error": {
    "message": "Unsupported parameter: stream_options",
    "type": "invalid_request_error",
    "param": "stream_options",
    "code": "unsupported_parameter"
  }
}
```

2. **Graceful Degradation:** Option to ignore unknown parameters instead of rejecting

---

## 7. Implementation Priorities

### Phase 1: Critical (P0) - Blocks Basic Functionality
1. ✅ Basic chat completions (DONE)
2. ❌ **Tool/Function calling** (REQUIRED FOR FULL CLINE)
   - Parse `tools` array
   - Support `tool_choice`
   - Return `tool_calls` in response
   - Support multi-turn tool conversations

### Phase 2: Important (P1) - Degrades UX
1. ❌ `stream_options` with usage statistics
2. ❌ Better error messages with bodies for 422
3. ⚠️ `parallel_tool_calls` support (or graceful ignore)

### Phase 3: Nice to Have (P2)
1. ❌ `reasoning_effort` parameter
2. ❌ Extended reasoning content in responses
3. ❌ Vision capabilities (if model supports)

---

## 8. Current Workaround: Proxy Solution

### 8.1 Architecture

```
Cline → Proxy (localhost:8081) → vLLM (172.30.0.54:8080)
```

### 8.2 Proxy Functionality

**Strips these parameters:**
- `stream_options`
- `parallel_tool_calls`
- `reasoning_effort`
- `tools` (if vLLM doesn't support)
- `tool_choice` (if vLLM doesn't support)

**Location:** `/Users/anders/temp/vllm_proxy.py`

### 8.3 Limitations of Proxy Approach

❌ **Cannot implement:**
- Tool calling (requires model cooperation)
- Reasoning content (requires model capability)

✅ **Can handle:**
- Parameter stripping
- Request/response transformation
- Error message enhancement

---

## 9. Testing Requirements

### 9.1 Test Cases for Tool Calling

```python
# Test 1: Single tool call
{
  "model": "gpt-oss-120b",
  "messages": [{"role": "user", "content": "Read the file /tmp/test.txt"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "read_file",
      "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}
    }
  }],
  "tool_choice": "auto"
}

# Expected: Model returns tool_call for read_file

# Test 2: Tool result continuation
{
  "messages": [
    {"role": "user", "content": "Read the file /tmp/test.txt"},
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "call_xxx", "content": "file contents"}
  ]
}

# Expected: Model processes tool result and responds
```

### 9.2 Test Cases for Stream Options

```python
{
  "stream": true,
  "stream_options": {"include_usage": true}
}

# Expected: Final chunk includes usage stats
```

---

## 10. OpenAI API Compatibility Matrix

| Feature | OpenAI | vLLM Current | Required by Cline | Priority |
|---------|--------|--------------|-------------------|----------|
| Basic chat | ✅ | ✅ | ✅ | P0 |
| Streaming | ✅ | ✅ | ✅ | P0 |
| Temperature/top_p | ✅ | ✅ | ✅ | P0 |
| max_tokens | ✅ | ✅ | ✅ | P0 |
| Tool calling | ✅ | ❌ | ✅ | P0 |
| tool_choice | ✅ | ❌ | ✅ | P0 |
| parallel_tool_calls | ✅ | ❌ | ✅ | P1 |
| stream_options | ✅ | ❌ | ✅ | P1 |
| reasoning_effort | ✅ | ❌ | ⚠️ | P2 |
| JSON mode | ✅ | ❌ | ⚠️ | P2 |
| Vision | ✅ | ❌ | ❌ | P3 |

---

## 11. Recommendations

### For vLLM Development Team

1. **Implement Tool Calling (Critical)**
   - This is the single most important feature for Cline compatibility
   - Enables all agentic workflows
   - Consider using existing frameworks (e.g., Hermes, Functionary prompting)

2. **Graceful Parameter Handling**
   - Don't reject requests with 422 for unknown parameters
   - Option 1: Ignore unknown parameters silently
   - Option 2: Return detailed error messages

3. **Stream Options Support**
   - Add `include_usage` to streaming responses
   - Low implementation cost, high value

### For Cline Users (Current State)

1. **Use the Proxy** (Required)
   - Located: `/Users/anders/temp/vllm_proxy.py`
   - Start: `./start_proxy.sh`
   - Strips incompatible parameters

2. **Limitations with Current Setup**
   - ❌ No tool calling → Cline can't perform actions
   - ❌ No file operations
   - ❌ No bash commands
   - ✅ Can do: Chat, code generation, text analysis

3. **API Key Setup**
   - CLI: `/Users/anders/.cline/data/secrets.json`
   - Key name: `"openAiApiKey"`
   - VS Code: Set via UI in Cline settings

---

## 12. Alternative Solutions

### 12.1 Use Different Model Provider

**Options:**
- Ollama (✅ Already configured: qwen3-coder:30b)
- LM Studio
- LocalAI (has better OpenAI compatibility)

**Trade-offs:**
- Ollama: Simpler API but different parameter requirements
- LocalAI: Better OpenAI compatibility, might work directly
- LM Studio: GUI-based, limited scriptability

### 12.2 Upgrade vLLM

Check if newer vLLM versions support:
- Tool calling (experimental in some versions)
- Better parameter handling
- OpenAI compatibility improvements

---

## 13. Conclusion

### Current State
- ✅ Basic chat works via proxy
- ❌ Full Cline functionality blocked by missing tool calling
- ⚠️ Workaround strips parameters but can't add missing features

### Required for Full Compatibility
**P0 (Blocking):**
1. Tool/function calling implementation
2. Multi-turn tool conversation support

**P1 (Degraded UX):**
1. Stream options with usage
2. Better error messages

**P2 (Nice to have):**
1. Extended reasoning support

### Estimated Implementation Effort

| Feature | Complexity | Effort | Value for Cline |
|---------|-----------|---------|-----------------|
| Tool calling | High | 2-3 weeks | Critical |
| Stream options | Low | 2-3 days | Medium |
| Error messages | Low | 1 day | Low |
| Reasoning | Medium | 1 week | Low |

---

## Appendix A: Cline Source Code References

**File:** `/opt/homebrew/lib/node_modules/cline/cline-core.js`

**Key Functions:**
- Line 839379-839388: OpenAI API request construction
- Line 813883-813891: Tool parameters generation
- Line 839386: `stream_options` hardcoded
- Line 839387: `parallel_tool_calls` via tool params

---

## Appendix B: Contact & Support

**Created by:** Claude (Anthropic)
**For:** Cline + vLLM integration
**Date:** 2025-11-12
**Proxy Location:** `/Users/anders/temp/vllm_proxy.py`
**Configuration:** `/Users/anders/.cline/data/globalState.json`

---

*Last Updated: 2025-11-12 10:15 CET*
