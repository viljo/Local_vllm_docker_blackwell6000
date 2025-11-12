# Implementation Plan: OpenAI-Compatible Tool Calling Support for Cline

**Branch**: `003-cline-tool-calling` | **Date**: 2025-11-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-cline-tool-calling/spec.md`

## Summary

This feature adds OpenAI-compatible function/tool calling support to the Local LLM Service router, enabling Cline and other AI coding assistants to execute local operations (file I/O, bash commands, etc.) through the API. The implementation uses a **prompt engineering approach** where tool definitions are injected into the system prompt and tool calls are extracted from model responses, avoiding vLLM's known streaming bugs while maintaining compatibility across all models.

**Technical Approach**:
1. Extend Pydantic models to accept tool-related parameters (`tools`, `tool_choice`, `parallel_tool_calls`)
2. Transform requests by injecting tool definitions into system prompts
3. Parse backend responses to extract tool call JSON structures
4. Transform responses to match OpenAI's format with `tool_calls` arrays
5. Support multi-turn conversations with tool result messages
6. Handle streaming responses with buffered tool detection

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104.1, Pydantic 2.5.0, httpx 0.25.1, tiktoken 0.5.2
**Storage**: N/A (stateless proxy)
**Testing**: pytest, httpx async testing
**Target Platform**: Linux server (Docker container)
**Project Type**: Web - Backend API proxy
**Performance Goals**: < 200ms transformation overhead, maintain 95th percentile latency
**Constraints**:
  - < 200ms overhead for tool call processing (SC-003)
  - Support 20 sequential tool calls without degradation (SC-008)
  - 100% request acceptance for valid OpenAI tool calling requests (SC-004)
**Scale/Scope**:
  - Single router instance handling 10-100 concurrent requests
  - Support 1-50 tools per request
  - Handle conversations with up to 20 tool call turns

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture ✅ PASS

**Compliance**: All services remain containerized. Tool calling is an enhancement to the existing router container, requires no new services or infrastructure changes.

**Implementation**: Changes confined to existing `router` service Python code. No docker-compose modifications needed.

### Principle II: Model Specialization ✅ PASS

**Compliance**: Tool calling works across all specialized models (Python coder, general-purpose, GPT-OSS). Prompt engineering approach is model-agnostic.

**Implementation**: Each model receives tool definitions in its system prompt. No model-specific configuration required.

### Principle III: OpenAI-Compatible API (IDE Integration) ✅ PASS

**Compliance**: This feature ENHANCES OpenAI compatibility by adding full tool/function calling support required by Cline and other IDE extensions.

**Implementation**: Extends existing `/v1/chat/completions` endpoint with OpenAI-standard `tools`, `tool_choice`, and response formats. Drop-in compatible with Cline configuration.

### Principle IV: Resource Efficiency ✅ PASS

**Compliance**: Minimal resource impact. Tool definitions add tokens to prompts (typically 100-500 tokens per request), but this is acceptable overhead for functionality gain.

**Implementation**:
- Request transformation: 2-5ms overhead
- Response transformation: 3-8ms overhead
- Token overhead: ~10-15% increase for requests with tools
- No additional memory or GPU requirements

### Principle V: Developer Experience ✅ PASS

**Compliance**: Enhances developer experience by enabling IDE tool integrations (Cline file operations, bash commands). Clear error messages for tool-related issues.

**Implementation**:
- Backward compatible (existing non-tool requests unchanged)
- Clear OpenAI-format error messages
- Comprehensive quickstart guide
- Detailed logging for debugging

**Constitution Check Result**: ✅ **PASS** - All principles complied with, no violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-cline-tool-calling/
├── spec.md                  # Feature specification (✅ Complete)
├── plan.md                  # This file (✅ Complete)
├── research.md              # Phase 0 research output (✅ Complete)
├── data-model.md            # Phase 1 data models (✅ Complete)
├── quickstart.md            # Phase 1 implementation guide (✅ Complete)
├── contracts/               # Phase 1 API contracts (✅ Complete)
│   └── tool-calling-api.yaml
├── checklists/              # Quality validation
│   └── requirements.md      # Spec quality checklist (✅ Complete)
└── tasks.md                 # Phase 2 output (/speckit.tasks - PENDING)
```

### Source Code (repository root)

```text
router/
├── app/
│   ├── main.py                  # MODIFY: Update models, endpoint logic
│   ├── transformations.py       # NEW: Tool injection/extraction logic
│   ├── tool_parsing.py          # NEW: Tool call detection and parsing
│   └── streaming.py             # NEW (Phase 2): Enhanced streaming handlers
├── requirements.txt             # UPDATE: No new dependencies needed
└── tests/
    ├── test_tool_calling.py     # NEW: Tool calling unit tests
    └── test_integration.py      # NEW: End-to-end integration tests

test_api_complete.py             # UPDATE: Add tool calling test cases
```

**Structure Decision**:

This is a backend-only enhancement to the existing web application. We're modifying the FastAPI router service without changing the frontend or vLLM backends. The architecture remains:

```
Frontend (WebUI) ─┐
                  ├─> Router (FastAPI) ──> vLLM Backends
Cline/IDEs ───────┘      ↑ (enhancements here)
```

Changes are isolated to the `router/` directory:
- **Existing**: `router/app/main.py` contains models and endpoints
- **New modules**: Separate transformation logic for maintainability
- **Tests**: New test files for tool calling functionality

---

## Implementation Phases

### Phase 0: Research ✅ COMPLETE

**Status**: Complete (see `research.md`)

**Deliverables**:
- [x] vLLM tool calling capability analysis
- [x] OpenAI API specification documentation
- [x] FastAPI middleware pattern research
- [x] Implementation approach decision (prompt engineering vs native)
- [x] Performance overhead estimates
- [x] Risk assessment and mitigation strategies

**Key Decisions**:
- Use prompt engineering approach (not vLLM native support)
- Stateless proxy design (no conversation storage)
- Flexible Pydantic models with `ConfigDict(extra='allow')`
- Buffer streaming responses for tool detection

### Phase 1: Design ✅ COMPLETE

**Status**: Complete (see `data-model.md`, `contracts/`, `quickstart.md`)

**Deliverables**:
- [x] Data model definitions (10 entities with relationships)
- [x] OpenAPI 3.1 contract specification
- [x] Quickstart implementation guide
- [x] Validation rules documented
- [x] Error handling patterns defined

**Key Artifacts**:
- **Entities**: ChatMessage, ToolCall, FunctionInvocation, ToolDefinition, ToolFunction, StreamOptions, ChatCompletionRequest, ChatCompletionResponse, Choice, UsageStatistics
- **API Contract**: Complete OpenAPI spec with examples
- **Quickstart**: Step-by-step 2-3 hour implementation path

### Phase 2: Implementation (NEXT - use /speckit.tasks)

**Status**: Pending task generation

**Expected Tasks**:
1. Update Pydantic models in `main.py`
2. Create `transformations.py` module
3. Implement tool injection logic
4. Implement tool extraction logic
5. Modify `/v1/chat/completions` endpoint
6. Add error handling
7. Write unit tests
8. Write integration tests
9. Test with Cline
10. Add logging and monitoring

**Estimated Time**: 5-8 days

### Phase 3: Optimization (FUTURE)

**Status**: Planned for after Phase 2

**Expected Enhancements**:
- Streaming with tool detection (buffered approach)
- Stream options with usage statistics
- Performance optimization (orjson, compiled regex)
- Enhanced error messages
- Tool call loop detection

---

## Design Artifacts

### 1. Data Models

**Location**: `data-model.md`

**Key Entities**:
- **ChatMessage**: Supports `role: "tool"`, optional `content`, `tool_calls` array
- **ToolCall**: Unique ID (format: `call_<random>`), function name and arguments
- **Tool**: Function definition with name, description, JSON Schema parameters
- **Request/Response**: Complete chat completion structures with tool support

**Validation Rules**:
- Tool call IDs must match between requests and results
- Tool role messages must include `tool_call_id`
- Tool function `arguments` must be valid JSON string
- Finish reason must be `"tool_calls"` when tools invoked

### 2. API Contracts

**Location**: `contracts/tool-calling-api.yaml`

**Specification**:
- OpenAPI 3.1 format
- Complete request/response schemas
- Error response formats
- Three example scenarios (simple chat, tool calling, multi-turn)
- Streaming response format (SSE)

**Endpoints**:
- `POST /v1/chat/completions` - Extended with tool support

### 3. Implementation Guide

**Location**: `quickstart.md`

**Contents**:
- 4-step implementation path (2-3 hours to MVP)
- Code samples for all changes
- Cline configuration instructions
- Troubleshooting guide
- Testing procedures

---

## Key Implementation Details

### Request Transformation Flow

```
Cline Request (with tools)
    ↓
Validate tools array
    ↓
Inject tools into system prompt
    ↓
Filter unsupported params (tools, tool_choice)
    ↓
Forward to vLLM backend
```

### Response Transformation Flow

```
vLLM Response (text)
    ↓
Extract tool_calls from content (regex + JSON parse)
    ↓
Inject tool_calls array into message
    ↓
Set finish_reason to "tool_calls"
    ↓
Set content to null (if all JSON)
    ↓
Return to Cline
```

### Multi-Turn Conversation Flow

```
Turn 1: User → Assistant (tool_calls)
Turn 2: Tool results → Assistant (final response)
Turn 3: User → ... (repeats)
```

---

## Testing Strategy

### Unit Tests (`test_tool_calling.py`)

```python
def test_tool_injection():
    """Verify tools injected into system prompt"""

def test_tool_extraction():
    """Verify tool_calls extracted from JSON blocks"""

def test_response_transformation():
    """Verify backend response transformed correctly"""

def test_validation_rules():
    """Verify tool_call_id matching and validation"""

def test_error_handling():
    """Verify OpenAI-format error messages"""
```

### Integration Tests (`test_integration.py`)

```python
async def test_end_to_end_tool_calling():
    """Full workflow: request → tool call → result → response"""

async def test_multi_turn_conversation():
    """Verify conversation context maintained across turns"""

async def test_parallel_tool_calls():
    """Verify multiple tool calls in single response"""

async def test_cline_compatibility():
    """Verify exact Cline request patterns work"""
```

### Manual Testing with Cline

1. Configure Cline to use `http://localhost:8080/v1`
2. Test file operations: "Read README.md"
3. Test bash commands: "List Python files"
4. Test multi-turn: "Read file X, then summarize it"
5. Monitor logs for tool call detection

---

## Performance Targets

| Metric | Target | Measured By |
|--------|--------|-------------|
| Transformation overhead | < 200ms | Response time delta |
| Tool call detection accuracy | > 95% | Test success rate |
| Request acceptance rate | 100% | Valid requests processed |
| Parallel execution speedup | > 40% reduction | Multi-tool workflow time |
| Usage stat accuracy | < 1% variance | Token count comparison |
| Sequential tool calls | 20 turns | Conversation depth tests |

**How to Measure**:
- Add timing decorators to transformation functions
- Log request start/end times
- Compare with and without tool processing
- Run load tests with various tool configurations

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Model doesn't follow JSON format | Use well-trained models (GPT-OSS, Qwen); add strict regex validation |
| Streaming latency increases | Acceptable trade-off; can optimize in Phase 3 |
| Tool call parsing false positives | Validate tool exists in request's tools array; log ambiguous cases |
| Backward compatibility breaks | Extensive testing of non-tool requests; use `extra='allow'` |
| Performance degradation | Profile hot paths; optimize JSON parsing; consider caching |

---

## Success Criteria Validation

| SC-ID | Criterion | Implementation Strategy |
|-------|-----------|------------------------|
| SC-001 | File operations work | Tool calling functional with proper error handling |
| SC-002 | Multi-turn conversations | Full message history support in requests |
| SC-003 | < 200ms overhead | Optimized transformation pipeline with minimal buffering |
| SC-004 | 100% acceptance | Flexible Pydantic models accept all valid requests |
| SC-005 | 40% faster parallel | Support `parallel_tool_calls` parameter |
| SC-006 | < 1% usage variance | Accurate token counting with tiktoken |
| SC-007 | Clear error messages | OpenAI-compatible error format with details |
| SC-008 | 20 sequential calls | No limits on conversation depth |
| SC-009 | 95% malformed detection | JSON schema validation on arguments |
| SC-010 | Backward compatibility | Existing requests unaffected by changes |

---

## Complexity Tracking

**Constitution Check Result**: No violations, table not needed.

All changes comply with existing architecture principles:
- Containerization maintained
- Model specialization preserved
- OpenAI compatibility enhanced
- Resource efficiency acceptable
- Developer experience improved

---

## Next Steps

1. ✅ **Complete /speckit.plan** (this file)
2. **Run /speckit.tasks** → Generate task breakdown from this plan
3. **Execute Phase 2** → Implement tasks sequentially
4. **Test with Cline** → Validate full integration
5. **Optimize Phase 3** → Enhance streaming and performance

---

## References

- **Feature Spec**: [spec.md](./spec.md)
- **Research**: [research.md](./research.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/tool-calling-api.yaml](./contracts/tool-calling-api.yaml)
- **Quickstart**: [quickstart.md](./quickstart.md)
- **Cline Requirements**: `/openai_api_requirements_for_cline.md`
- **Current Router**: `/router/app/main.py`

---

**Plan Status**: ✅ **COMPLETE**
**Phase 0**: ✅ Research Complete
**Phase 1**: ✅ Design Complete
**Phase 2**: ⏳ Pending `/speckit.tasks`
**Ready for Implementation**: Yes

**Last Updated**: 2025-11-12
