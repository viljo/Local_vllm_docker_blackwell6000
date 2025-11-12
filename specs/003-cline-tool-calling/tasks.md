# Implementation Tasks: OpenAI-Compatible Tool Calling Support for Cline

**Feature**: 003-cline-tool-calling
**Branch**: `003-cline-tool-calling`
**Generated**: 2025-11-12

## Overview

This document breaks down the implementation of tool calling support into specific, actionable tasks organized by user story priority. Each phase represents an independently testable increment of functionality that delivers value.

**Implementation Strategy**: Incremental delivery by user story priority
- **MVP**: User Story 1 (Basic Tool Invocation) + User Story 2 (Multi-Turn) = Complete working tool calling
- **Enhancement 1**: User Story 3 (Parallel Execution)
- **Enhancement 2**: User Story 4 (Streaming with Usage) + User Story 5 (Graceful Parameters)

---

## Task Legend

- `[ ]` = Not started
- `[X]` = Completed
- **[P]** = Parallelizable (can run concurrently with other [P] tasks in same phase)
- **[US#]** = User Story number (US1, US2, US3, etc.)
- **Task ID** = Sequential task number (T001, T002, etc.)

---

## Phase 1: Setup & Foundation

**Goal**: Prepare project structure and foundational components needed for all user stories

**Duration**: 1-2 hours

### Setup Tasks

- [X] T001 Verify Python 3.11+ environment in router container
- [X] T002 Verify existing dependencies (FastAPI 0.104.1, Pydantic 2.5.0, httpx 0.25.1) in router/requirements.txt
- [X] T003 Create router/app/transformations.py module for tool transformation logic
- [X] T004 Create router/app/tool_parsing.py module for tool call detection
- [X] T005 Add import statements for new modules in router/app/main.py

### Foundational Tasks (Blocking - must complete before user stories)

- [X] T006 Update ChatMessage Pydantic model in router/app/main.py to support tool role and optional fields
- [X] T007 Create ToolFunction Pydantic model in router/app/main.py
- [X] T008 Create Tool Pydantic model in router/app/main.py
- [X] T009 Update ChatCompletionRequest model in router/app/main.py with ConfigDict(extra='allow')
- [X] T010 Add tools, tool_choice, parallel_tool_calls, stream_options fields to ChatCompletionRequest

**Phase 1 Completion Criteria**:
- ✅ All Pydantic models support tool-related fields
- ✅ Request model accepts unknown parameters gracefully
- ✅ New modules created and importable
- ✅ No breaking changes to existing non-tool requests

---

## Phase 2: User Story 1 - Basic Tool Invocation (P1 - MVP)

**Goal**: Enable basic tool calling - request with tools → response with tool_calls

**Independent Test**: Send chat completion with tools array, verify response contains tool_calls with correct structure

**Duration**: 3-4 hours

### US1 Implementation Tasks

- [X] T011 [US1] Implement generate_tool_call_id() function in router/app/tool_parsing.py
- [X] T012 [US1] Implement tools_to_system_prompt() function in router/app/transformations.py
- [X] T013 [US1] Implement inject_tools_into_messages() function in router/app/transformations.py
- [X] T014 [US1] Implement extract_tool_calls_from_text() function with JSON code block pattern in router/app/tool_parsing.py
- [X] T015 [US1] Add XML-style tool call pattern support to extract_tool_calls_from_text() in router/app/tool_parsing.py
- [X] T016 [US1] Implement transform_response_with_tools() function in router/app/transformations.py
- [X] T017 [US1] Modify /v1/chat/completions endpoint in router/app/main.py to call inject_tools_into_messages()
- [X] T018 [US1] Add payload filtering logic in router/app/main.py to remove unsupported tool params before backend forward
- [X] T019 [US1] Add response transformation call in router/app/main.py for non-streaming responses
- [X] T020 [US1] Add error handling for malformed tool definitions in router/app/main.py

### US1 Testing Tasks

- [ ] T021 [P] [US1] Create test_tool_calling.py in router/tests/ with basic tool invocation test
- [ ] T022 [P] [US1] Add test for tool_choice="auto" behavior in router/tests/test_tool_calling.py
- [ ] T023 [P] [US1] Add test for tool_choice="none" behavior in router/tests/test_tool_calling.py
- [ ] T024 [P] [US1] Add test for specific tool selection via tool_choice in router/tests/test_tool_calling.py
- [ ] T025 [P] [US1] Add test for tools_to_system_prompt() in router/tests/test_tool_calling.py
- [ ] T026 [P] [US1] Add test for extract_tool_calls_from_text() JSON extraction in router/tests/test_tool_calling.py
- [ ] T027 [P] [US1] Add test for transform_response_with_tools() in router/tests/test_tool_calling.py

**Phase 2 Completion Criteria**:
- ✅ API accepts requests with tools array without validation errors (FR-001, SC-004)
- ✅ Tool definitions injected into system prompt
- ✅ Model responses parsed for tool_calls
- ✅ Response includes tool_calls array with proper structure (FR-006)
- ✅ finish_reason set to "tool_calls" when tools invoked (FR-008)
- ✅ Unique tool_call_id generated for each invocation (FR-016)
- ✅ All US1 tests pass

**Independent Test Command**:
```bash
pytest router/tests/test_tool_calling.py::test_basic_tool_invocation -v
```

---

## Phase 3: User Story 2 - Multi-Turn Tool Conversations (P1 - MVP)

**Goal**: Support complete tool workflow - tool_calls → tool results → final response

**Independent Test**: Send 3-message conversation (user → assistant with tool_calls → tool result), verify assistant processes result

**Duration**: 2-3 hours

### US2 Implementation Tasks

- [X] T028 [US2] Add validation for role="tool" messages in router/app/main.py ChatMessage model
- [X] T029 [US2] Add tool_call_id validation in router/app/transformations.py
- [X] T030 [US2] Implement validate_tool_result_messages() function in router/app/transformations.py
- [X] T031 [US2] Add conversation context preservation logic in router/app/main.py endpoint
- [X] T032 [US2] Add error handling for mismatched tool_call_id in router/app/transformations.py
- [X] T033 [US2] Add logging for multi-turn tool conversations in router/app/main.py

### US2 Testing Tasks

- [ ] T034 [P] [US2] Add test for tool role message acceptance in router/tests/test_tool_calling.py
- [ ] T035 [P] [US2] Add test for tool_call_id matching validation in router/tests/test_tool_calling.py
- [ ] T036 [P] [US2] Add test for complete 3-turn conversation flow in router/tests/test_tool_calling.py
- [ ] T037 [P] [US2] Add test for multiple sequential tool calls in router/tests/test_tool_calling.py
- [ ] T038 [P] [US2] Add test for error handling when tool_call_id mismatch in router/tests/test_tool_calling.py

**Phase 3 Completion Criteria**:
- ✅ API accepts messages with role="tool" (FR-004)
- ✅ tool_call_id validated against previous tool_calls (FR-014)
- ✅ Conversation context maintained across turns (FR-009, SC-002)
- ✅ Multi-turn conversations work end-to-end
- ✅ All US2 tests pass

**Independent Test Command**:
```bash
pytest router/tests/test_tool_calling.py::test_multi_turn_conversation -v
```

---

## Phase 4: User Story 3 - Parallel Tool Execution (P2 - Enhancement)

**Goal**: Support multiple tool_calls in single response for improved performance

**Independent Test**: Send request requiring multiple operations, verify response contains multiple tool_calls with distinct IDs

**Duration**: 2-3 hours

### US3 Implementation Tasks

- [X] T039 [US3] Add parallel_tool_calls parameter handling in router/app/main.py
- [X] T040 [US3] Enhance extract_tool_calls_from_text() to detect multiple tool calls in router/app/tool_parsing.py
- [X] T041 [US3] Add multiple tool_call_id generation in router/app/tool_parsing.py
- [X] T042 [US3] Update transform_response_with_tools() to handle multiple tool_calls in router/app/transformations.py
- [X] T043 [US3] Add validation for all tool results when parallel calls used in router/app/transformations.py

### US3 Testing Tasks

- [ ] T044 [P] [US3] Add test for parallel_tool_calls=true with multiple tools in router/tests/test_tool_calling.py
- [ ] T045 [P] [US3] Add test for multiple tool results processing in router/tests/test_tool_calling.py
- [ ] T046 [P] [US3] Add test for parallel_tool_calls=false limiting to one call in router/tests/test_tool_calling.py
- [ ] T047 [P] [US3] Add performance test comparing sequential vs parallel execution times in router/tests/test_tool_calling.py

**Phase 4 Completion Criteria**:
- ✅ parallel_tool_calls parameter accepted (FR-003)
- ✅ Multiple tool_calls returned in single response when appropriate
- ✅ Each tool call has unique ID
- ✅ Multiple tool results processed correctly (FR-020)
- ✅ 40% performance improvement measured for 3+ tool workflows (SC-005)
- ✅ All US3 tests pass

**Independent Test Command**:
```bash
pytest router/tests/test_tool_calling.py::test_parallel_tool_calls -v
```

---

## Phase 5: User Story 4 - Streaming with Usage Statistics (P3 - Enhancement)

**Goal**: Add token usage statistics to streaming responses

**Independent Test**: Send streaming request with stream_options.include_usage=true, verify final chunk contains usage stats

**Duration**: 3-4 hours

### US4 Implementation Tasks

- [X] T048 [US4] Create router/app/streaming.py module for streaming handlers
- [X] T049 [US4] Implement stream_with_tool_detection() function with buffering in router/app/streaming.py
- [X] T050 [US4] Implement create_usage_chunk() function using tiktoken in router/app/streaming.py
- [X] T051 [US4] Add stream_options parameter handling in router/app/main.py
- [X] T052 [US4] Modify streaming branch in /v1/chat/completions to use enhanced streaming in router/app/main.py
- [X] T053 [US4] Add usage statistics calculation for streaming responses in router/app/streaming.py
- [X] T054 [US4] Add tool call detection in streaming chunks in router/app/streaming.py

### US4 Testing Tasks

- [ ] T055 [P] [US4] Add test for stream_options.include_usage in router/tests/test_tool_calling.py
- [ ] T056 [P] [US4] Add test for usage statistics in final streaming chunk in router/tests/test_tool_calling.py
- [ ] T057 [P] [US4] Add test for streaming with tool_calls and usage in router/tests/test_tool_calling.py
- [ ] T058 [P] [US4] Add test for usage statistics accuracy (< 1% variance) in router/tests/test_tool_calling.py

**Phase 5 Completion Criteria**:
- ✅ stream_options parameter accepted (FR-010)
- ✅ Usage statistics included in final streaming chunk when requested (FR-011)
- ✅ Token counts accurate within 1% (SC-006)
- ✅ Streaming with tool_calls works correctly
- ✅ All US4 tests pass

**Independent Test Command**:
```bash
pytest router/tests/test_tool_calling.py::test_streaming_with_usage -v
```

---

## Phase 6: User Story 5 - Graceful Parameter Handling (P3 - Enhancement)

**Goal**: Accept and gracefully handle unknown/unsupported parameters for forward compatibility

**Independent Test**: Send requests with various unsupported parameters, verify no validation errors

**Duration**: 1-2 hours

### US5 Implementation Tasks

- [X] T059 [US5] Verify ConfigDict(extra='allow') on all Pydantic models in router/app/main.py
- [X] T060 [US5] Implement parameter filtering in transform_request_for_backend() in router/app/transformations.py
- [X] T061 [US5] Add logging for unsupported parameters in router/app/main.py
- [X] T062 [US5] Implement OpenAI-compatible error format in router/app/main.py
- [X] T063 [US5] Add detailed error messages for common validation failures in router/app/main.py

### US5 Testing Tasks

- [ ] T064 [P] [US5] Add test for unsupported parameter acceptance in router/tests/test_tool_calling.py
- [ ] T065 [P] [US5] Add test for parameter filtering before backend forward in router/tests/test_tool_calling.py
- [ ] T066 [P] [US5] Add test for OpenAI error format on invalid values in router/tests/test_tool_calling.py
- [ ] T067 [P] [US5] Add test for clear error messages in router/tests/test_tool_calling.py

**Phase 6 Completion Criteria**:
- ✅ Unknown parameters accepted without errors (FR-012, SC-004)
- ✅ Only supported params forwarded to backend
- ✅ Error messages in OpenAI format (FR-013)
- ✅ Clear, actionable error messages (SC-007)
- ✅ All US5 tests pass

**Independent Test Command**:
```bash
pytest router/tests/test_tool_calling.py::test_graceful_parameters -v
```

---

## Phase 7: Integration & Edge Cases

**Goal**: Comprehensive integration testing and edge case handling

**Duration**: 2-3 hours

### Integration Tasks

- [ ] T068 Create test_integration.py in router/tests/ for end-to-end scenarios
- [ ] T069 [P] Add end-to-end test for complete Cline workflow (user request → tool call → execution → result → final response) in router/tests/test_integration.py
- [ ] T070 [P] Add test for 20 sequential tool calls to verify conversation depth limit in router/tests/test_integration.py
- [ ] T071 [P] Add test for 50 tools in single request to verify scale handling in router/tests/test_integration.py
- [ ] T072 [P] Add test for malformed JSON in tool arguments in router/tests/test_integration.py
- [ ] T073 [P] Add test for extremely large tool definitions in router/tests/test_integration.py
- [ ] T074 [P] Add test for missing required tool definition fields in router/tests/test_integration.py
- [ ] T075 [P] Add test for messages with both content and tool_calls in router/tests/test_integration.py
- [ ] T076 [P] Add test for tool results in wrong order in router/tests/test_integration.py

### Performance & Validation Tasks

- [ ] T077 Add performance timing decorator to transformation functions in router/app/transformations.py
- [ ] T078 Add logging for request/response transformation times in router/app/main.py
- [ ] T079 [P] Add performance test verifying < 200ms transformation overhead in router/tests/test_integration.py
- [ ] T080 [P] Add load test for 10-100 concurrent tool calling requests in router/tests/test_integration.py

**Phase 7 Completion Criteria**:
- ✅ All edge cases handled gracefully
- ✅ Integration tests cover complete workflows
- ✅ Performance targets met (< 200ms overhead - SC-003)
- ✅ System handles 20 sequential tool calls (SC-008)
- ✅ Error handling comprehensive (SC-007, SC-009)
- ✅ All integration tests pass

**Independent Test Command**:
```bash
pytest router/tests/test_integration.py -v
```

---

## Phase 8: Polish & Documentation

**Goal**: Code quality, documentation, and production readiness

**Duration**: 2-3 hours

### Polish Tasks

- [ ] T081 [P] Add comprehensive docstrings to all functions in router/app/transformations.py
- [ ] T082 [P] Add comprehensive docstrings to all functions in router/app/tool_parsing.py
- [ ] T083 [P] Add type hints to all functions in router/app/transformations.py
- [ ] T084 [P] Add type hints to all functions in router/app/tool_parsing.py
- [ ] T085 [P] Add inline comments for complex regex patterns in router/app/tool_parsing.py
- [ ] T086 [P] Add logging statements at key decision points in router/app/transformations.py
- [ ] T087 Run ruff check on modified files and fix any issues
- [ ] T088 Run pytest with coverage report, verify > 80% coverage for new code

### Documentation Tasks

- [ ] T089 [P] Update test_api_complete.py with tool calling test cases
- [ ] T090 [P] Add example tool calling requests to test_api_complete.py
- [ ] T091 [P] Create TESTING.md in specs/003-cline-tool-calling/ with test execution guide
- [ ] T092 [P] Add troubleshooting section to specs/003-cline-tool-calling/quickstart.md for common issues

**Phase 8 Completion Criteria**:
- ✅ All code properly documented
- ✅ Type hints complete
- ✅ Code passes linting checks
- ✅ Test coverage > 80%
- ✅ Testing documentation complete
- ✅ All polish tasks complete

---

## Dependencies & Execution Order

### Critical Path (Must execute sequentially)

```
Phase 1 (Setup & Foundation)
  ↓
Phase 2 (User Story 1 - Basic Tool Invocation)
  ↓
Phase 3 (User Story 2 - Multi-Turn Conversations)
  ↓
Phase 4, 5, 6 can run in parallel (independent user stories)
  ↓
Phase 7 (Integration & Edge Cases)
  ↓
Phase 8 (Polish & Documentation)
```

### Parallel Execution Opportunities

**Within Phase 2 (US1)**:
- T021-T027 (all US1 tests) can run in parallel after T011-T020 complete

**Within Phase 3 (US2)**:
- T034-T038 (all US2 tests) can run in parallel after T028-T033 complete

**Within Phase 4 (US3)**:
- T044-T047 (all US3 tests) can run in parallel after T039-T043 complete

**Within Phase 5 (US4)**:
- T055-T058 (all US4 tests) can run in parallel after T048-T054 complete

**Within Phase 6 (US5)**:
- T064-T067 (all US5 tests) can run in parallel after T059-T063 complete

**Within Phase 7**:
- T069-T076 (all integration tests) can run in parallel after T068 completes
- T079-T080 (performance tests) can run in parallel

**Within Phase 8**:
- All documentation tasks (T089-T092) can run in parallel
- All polish tasks (T081-T086) can run in parallel

### MVP Scope (Recommended first delivery)

**Minimum Viable Product**: Phases 1-3 only
- Phase 1: Setup & Foundation (T001-T010)
- Phase 2: User Story 1 - Basic Tool Invocation (T011-T027)
- Phase 3: User Story 2 - Multi-Turn Conversations (T028-T038)

**Result**: Complete working tool calling that enables Cline file operations and basic workflows

**Estimated Time**: 6-9 hours of focused development

---

## Task Summary

| Phase | Description | Tasks | Parallelizable | Duration |
|-------|-------------|-------|----------------|----------|
| 1 | Setup & Foundation | T001-T010 (10) | 0 | 1-2h |
| 2 | US1: Basic Tool Invocation | T011-T027 (17) | 7 | 3-4h |
| 3 | US2: Multi-Turn Conversations | T028-T038 (11) | 5 | 2-3h |
| 4 | US3: Parallel Execution | T039-T047 (9) | 4 | 2-3h |
| 5 | US4: Streaming with Usage | T048-T058 (11) | 4 | 3-4h |
| 6 | US5: Graceful Parameters | T059-T067 (9) | 4 | 1-2h |
| 7 | Integration & Edge Cases | T068-T080 (13) | 10 | 2-3h |
| 8 | Polish & Documentation | T081-T092 (12) | 11 | 2-3h |
| **Total** | **All Features** | **92 tasks** | **45 parallel** | **16-24h** |

---

## Success Criteria Validation

| Success Criterion | Validated By Tasks | Phase |
|-------------------|-------------------|-------|
| SC-001: File operations work | T021, T069 (integration test) | 2, 7 |
| SC-002: Multi-turn conversations | T036-T037, T070 | 3, 7 |
| SC-003: < 200ms overhead | T077-T079 (performance tests) | 7 |
| SC-004: 100% acceptance | T022-T024, T064-T065 | 2, 6 |
| SC-005: 40% parallel speedup | T047 (performance comparison) | 4 |
| SC-006: < 1% usage variance | T058 (usage accuracy test) | 5 |
| SC-007: Clear error messages | T062-T063, T067 | 6 |
| SC-008: 20 sequential calls | T070 (depth limit test) | 7 |
| SC-009: 95% malformed detection | T072, T074 (validation tests) | 7 |
| SC-010: Backward compatibility | All existing tests must pass | All |

---

## Implementation Notes

1. **Testing Philosophy**: Tests are included for validation but not strictly TDD. Implement core functionality first, then validate with tests.

2. **MVP-First Approach**: Complete Phases 1-3 for a working MVP before enhancing with Phases 4-6.

3. **Parallel Execution**: Use task markers [P] to identify tasks that can run concurrently within a phase.

4. **File Coordination**: Tasks affecting the same file must run sequentially to avoid conflicts.

5. **Error Handling**: Halt on non-parallel task failures, continue with partial success for parallel tasks.

6. **Checkpoints**: Validate phase completion criteria before proceeding to next phase.

7. **Performance**: Monitor transformation overhead throughout implementation (target < 200ms).

8. **Documentation**: Update docs incrementally as features are completed.

---

## Next Steps

After task generation:
1. Run `/speckit.implement` to execute tasks automatically
2. Or manually execute tasks in order, marking completed with `[X]`
3. Validate each phase completion criteria before proceeding
4. Run integration tests at Phase 7 to verify all features work together

**Ready for Implementation**: Yes
**Task Breakdown**: Complete
**Estimated Total Time**: 16-24 hours (MVP: 6-9 hours)

---

**Generated**: 2025-11-12
**Status**: Ready for execution
**Command**: `/speckit.implement` to begin automated implementation
