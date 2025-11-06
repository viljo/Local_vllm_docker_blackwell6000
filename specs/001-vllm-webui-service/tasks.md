---

description: "Task list for Local AI Service with vLLM and WebUI"
---

# Tasks: Local AI Service with vLLM and WebUI

**Input**: Design documents from `/specs/001-vllm-webui-service/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL per specification. Not included in this task list.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Docker orchestration**: Repository root (`docker-compose.yml`, `.env.example`)
- **Router middleware**: `router/` (Python FastAPI)
- **WebUI frontend**: `frontend/` (React TypeScript)
- **Documentation**: `docs/`
- **Persistent volumes**: `models/`, `data/`, `config/` (host mounts)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure required by all user stories

- [ ] T001 Create project directory structure per plan.md (root, router/, frontend/, docs/, models/, data/, config/)
- [ ] T002 Create `.gitignore` file (exclude .env, models/, data/, node_modules/, __pycache__, *.pyc)
- [ ] T003 Create `.env.example` file with all required configuration variables (API_KEY, model IDs, ports, GPU memory settings)
- [ ] T004 [P] Create README.md with project overview, prerequisites, and link to quickstart.md
- [ ] T005 [P] Copy quickstart.md from specs/ to docs/quickstart.md as deployment guide

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Docker Infrastructure

- [ ] T006 Create `docker-compose.yml` with service definitions (vllm-coder, vllm-general, vllm-router, webui-frontend)
- [ ] T007 Configure vllm-coder service in docker-compose.yml (image: vllm/vllm-openai:latest, GPU passthrough, port 8000, volume mounts, command flags per research.md)
- [ ] T008 Configure vllm-general service in docker-compose.yml (image: vllm/vllm-openai:latest, GPU passthrough, port 8001, volume mounts, command flags per research.md)
- [ ] T009 Configure Docker networks in docker-compose.yml (internal network for service-to-service, external for client access)
- [ ] T010 [P] Configure volume mounts in docker-compose.yml (./models:/models, ./data:/data, ./config:/config)

### Router Service Foundation

- [ ] T011 Initialize router service structure (router/main.py, router/requirements.txt, router/Dockerfile)
- [ ] T012 Create router/requirements.txt with dependencies (fastapi, uvicorn, httpx, prometheus-client)
- [ ] T013 Create router/Dockerfile with Python 3.11 base image and dependency installation
- [ ] T014 Configure router service in docker-compose.yml (build context, port 8080, environment variables, depends_on)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - IDE Code Assistance (Priority: P1) 🎯 MVP

**Goal**: Enable developers to use IDE extensions (Continue.dev, Cody, etc.) with local models for code completions and chat

**Independent Test**: Configure Continue.dev extension in VS Code to point to `http://localhost:8080/v1`, send code completion request, verify streamed response from DeepSeek Coder model

### Router Implementation for IDE Support

- [ ] T015 [US1] Implement FastAPI app initialization in router/main.py (app instance, CORS configuration for localhost origins)
- [ ] T016 [US1] Implement API key authentication middleware in router/main.py (bearer token validation against env var, 401 response on failure)
- [ ] T017 [US1] Implement backend routing logic in router/main.py (parse model parameter, map to vllm-coder or vllm-general URL)
- [ ] T018 [US1] Implement `/v1/chat/completions` endpoint in router/main.py (forward to selected backend with streaming support via httpx AsyncClient)
- [ ] T019 [US1] Implement `/v1/completions` endpoint in router/main.py (forward to selected backend, legacy format support)
- [ ] T020 [US1] Implement `/v1/models` endpoint in router/main.py (aggregate model list from both backends, include status field)
- [ ] T021 [US1] Implement `/health` endpoint in router/main.py (basic liveness check, return 200 with {"status": "healthy"})
- [ ] T022 [US1] Implement `/ready` endpoint in router/main.py (check both backends, return 200 if at least one model ready per FR-004)
- [ ] T023 [US1] Implement error handling in router/main.py (catch httpx exceptions, return 503 with Retry-After for backend errors)
- [ ] T024 [US1] Implement request logging in router/main.py (structured JSON logs with request ID, model, latency, status code per FR-008)
- [ ] T025 [US1] Implement log rotation configuration in router/main.py (7 days or 10GB limit per clarification Q5)

### Documentation for IDE Setup

- [ ] T026 [P] [US1] Create docs/ide-setup.md with configuration examples for Continue.dev, Cursor, JetBrains AI Assistant, and Neovim copilot.lua
- [ ] T027 [P] [US1] Add IDE troubleshooting section to docs/ide-setup.md (connection issues, API key errors, model selection problems)

### Deployment & Validation

- [ ] T028 [US1] Add router service build and startup logic to docker-compose.yml
- [ ] T029 [US1] Verify `.env.example` contains all router configuration (API_KEY, backend URLs, log settings)
- [ ] T030 [US1] Create validation script in docs/validate-us1.sh (test health, ready, models endpoints, chat completion with curl)

**Checkpoint**: At this point, IDE integration (MVP) should be fully functional and testable independently. Developers can connect Continue.dev and get code completions.

---

## Phase 4: User Story 2 - Browser Chat Interface (Priority: P2)

**Goal**: Provide ChatGPT-like WebUI for browser-based interaction with AI models

**Independent Test**: Open browser to `http://localhost:3000`, type message in chat interface, verify streamed response displays token by token

### Frontend Project Setup

- [ ] T031 [US2] Initialize React TypeScript project in frontend/ using Vite (npm create vite@latest frontend -- --template react-ts)
- [ ] T032 [US2] Install dependencies in frontend/ (react, react-dom, openai, @tanstack/react-query, typescript, vite)
- [ ] T033 [US2] Configure Vite in frontend/vite.config.ts (proxy API requests to router, HMR settings, build output)
- [ ] T034 [US2] Create frontend/tsconfig.json with strict TypeScript settings
- [ ] T035 [US2] Create frontend/.env.example with VITE_API_BASE_URL and VITE_API_KEY placeholders

### Frontend Core Components

- [ ] T036 [P] [US2] Create frontend/src/components/ChatInterface.tsx (main layout with message list and input areas)
- [ ] T037 [P] [US2] Create frontend/src/components/MessageList.tsx (display user and assistant messages, auto-scroll to bottom)
- [ ] T038 [P] [US2] Create frontend/src/components/MessageInput.tsx (textarea with send button and Ctrl+Enter shortcut)
- [ ] T039 [P] [US2] Create frontend/src/components/ConnectionStatus.tsx (indicator showing backend health, color-coded status)

### Frontend Services & State Management

- [ ] T040 [US2] Create frontend/src/services/api.ts (OpenAI SDK client wrapper with base URL and API key from env)
- [ ] T041 [US2] Create frontend/src/services/conversationManager.ts (token counting with js-tiktoken, 75% context window limit enforcement)
- [ ] T042 [US2] Create frontend/src/hooks/useChat.ts (useReducer for chat state, streaming logic per research.md React patterns)
- [ ] T043 [US2] Create frontend/src/hooks/useModels.ts (fetch available models from /v1/models, cache with TanStack Query)
- [ ] T044 [US2] Implement streaming response handler in useChat.ts (for await...of with OpenAI SDK, accumulate chunks via useRef)
- [ ] T045 [US2] Implement stop generation logic in useChat.ts (AbortController pattern per research.md)
- [ ] T046 [US2] Implement conversation context management in useChat.ts (dynamic truncation when exceeding 75% limit)
- [ ] T047 [US2] Implement session storage persistence in useChat.ts (save/restore conversation history from sessionStorage)

### Frontend Root & Styling

- [ ] T048 [US2] Create frontend/src/App.tsx (render ChatInterface, wrap with TanStack Query provider)
- [ ] T049 [US2] Create frontend/src/main.tsx (React root render, mount to DOM)
- [ ] T050 [P] [US2] Create frontend/src/index.css with minimal ChatGPT-like styling (clean layout, message bubbles, dark mode optional)

### Frontend Dockerfile & Integration

- [ ] T051 [US2] Create frontend/Dockerfile (multi-stage: npm install, npm build, nginx serve)
- [ ] T052 [US2] Configure webui-frontend service in docker-compose.yml (build context, port 3000, environment variables, depends_on router)
- [ ] T053 [US2] Add frontend/nginx.conf for serving built app and proxying API requests

### Validation

- [ ] T054 [US2] Create docs/validate-us2.sh (test WebUI loads, send message via UI automation or manual steps)

**Checkpoint**: At this point, both IDE (US1) AND WebUI (US2) should work independently. Users can choose their preferred interface.

---

## Phase 5: User Story 3 - Model Selection (Priority: P3)

**Goal**: Enable users to switch between Python-specialized and general-purpose models for task optimization

**Independent Test**: Send API request with `model: "deepseek-coder-33b-instruct"`, verify Python model responds; switch to `model: "mistral-7b-v0.1"`, verify general model responds

### Backend Model Routing Enhancement

- [ ] T055 [US3] Enhance router model routing in router/main.py (support explicit model IDs: deepseek-coder, qwen-coder, mistral, qwen-general)
- [ ] T056 [US3] Add fallback logic in router/main.py (default to general model if model parameter missing or unrecognized)
- [ ] T057 [US3] Enhance `/v1/models` endpoint to include model metadata (specialization field: "python-coding" or "general-purpose")
- [ ] T058 [US3] Add model status aggregation in `/ready` endpoint (return per-model status: loading, ready, error)

### Frontend Model Selector Component

- [ ] T059 [P] [US3] Create frontend/src/components/ModelSelector.tsx (dropdown with model list, display specialization, onChange handler)
- [ ] T060 [US3] Integrate ModelSelector into ChatInterface.tsx (place above message input, persist selection in state)
- [ ] T061 [US3] Update useChat.ts to pass selected model ID in API requests
- [ ] T062 [US3] Update useModels.ts to fetch and parse model metadata (specialization, context window size)

### IDE Documentation Update

- [ ] T063 [P] [US3] Update docs/ide-setup.md with multi-model configuration examples (show how to specify model per IDE tool)

### Validation

- [ ] T064 [US3] Create docs/validate-us3.sh (test model switching via curl, verify routing to correct backend)

**Checkpoint**: All user stories (US1, US2, US3) should now be independently functional. Model selection works in both IDE and WebUI contexts.

---

## Phase 6: User Story 4 - Single-Command Deployment (Priority: P4)

**Goal**: Enable one-command deployment for users with no Docker experience

**Independent Test**: Run `docker compose up` on fresh machine with NVIDIA drivers, verify all services start, health checks pass, WebUI accessible

### Deployment Polish

- [ ] T065 [US4] Verify docker-compose.yml has all services properly configured (dependencies, networks, volumes, restart policies)
- [ ] T066 [US4] Add health checks to docker-compose.yml for all services (interval, timeout, retries, start_period per service)
- [ ] T067 [US4] Verify `.env.example` is complete and well-documented (comments explaining each variable, safe defaults)
- [ ] T068 [US4] Create setup validation script in docs/setup-check.sh (verify Docker, nvidia-smi, NVIDIA Container Toolkit, disk space)

### Startup & Logging Improvements

- [ ] T069 [US4] Add startup progress logging to router/main.py (log when connecting to each backend, model availability updates)
- [ ] T070 [US4] Configure log levels in docker-compose.yml (INFO for production, DEBUG option via env var)
- [ ] T071 [US4] Add graceful shutdown handlers in router/main.py (close httpx clients, flush logs on SIGTERM)

### Documentation Finalization

- [ ] T072 [US4] Verify README.md links to quickstart.md and all setup documentation
- [ ] T073 [US4] Add troubleshooting section to README.md (common issues: OOM, port conflicts, API key errors)
- [ ] T074 [P] [US4] Create docs/architecture-diagram.md with ASCII diagram of service topology (per quickstart.md example)

### End-to-End Validation

- [ ] T075 [US4] Create docs/validate-all.sh (comprehensive test: health, ready, models, IDE request, WebUI request, model switching)
- [ ] T076 [US4] Test `docker compose up` from clean state (verify model downloads, progressive availability, final readiness)
- [ ] T077 [US4] Test `docker compose down` (verify clean shutdown, GPU resource release, no orphaned processes)

**Checkpoint**: Deployment should be a single command with clear progress indicators. All services start cleanly and release resources properly.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, final quality assurance

### Performance & Monitoring

- [ ] T078 [P] Add Prometheus metrics export in router/main.py (request count, latency histograms, error rates)
- [ ] T079 [P] Create docs/monitoring.md (explain Prometheus metrics, nvidia-smi usage, log analysis)

### Security & Configuration

- [ ] T080 [P] Add input validation in router/main.py (max message length, token limits, sanitize model parameter)
- [ ] T081 [P] Add rate limiting middleware in router/main.py (simple per-IP limits, configurable via env)
- [ ] T082 [P] Document security considerations in README.md (API key rotation, HTTPS setup, network isolation)

### Error Handling Enhancements

- [ ] T083 Add retry logic with exponential backoff in router/main.py (for 429/503 from backends per research.md)
- [ ] T084 Add client disconnection detection in router/main.py (remove queued requests per FR-009a)
- [ ] T085 Add detailed error responses in router/main.py (include model status, queue position, retry guidance)

### Frontend Polish

- [ ] T086 [P] Add loading states to WebUI (spinner during streaming, skeleton for message list)
- [ ] T087 [P] Add error display in WebUI (toast notifications for API errors, connection status banner)
- [ ] T088 [P] Add keyboard shortcuts to WebUI (Ctrl+K for new conversation, Ctrl+/ for help modal)
- [ ] T089 [P] Add context usage indicator in WebUI (progress bar showing 75% limit, color changes at thresholds)

### Documentation & Examples

- [ ] T090 [P] Create docs/api-examples.md with curl examples for all endpoints (/v1/chat/completions streaming, /v1/models, /health)
- [ ] T091 [P] Add FAQ section to README.md (model recommendations, VRAM usage, performance tuning)
- [ ] T092 [P] Create CONTRIBUTING.md with development setup (local dev without Docker, testing procedures)

### Final Validation

- [ ] T093 Run complete validation suite (docs/validate-all.sh) and verify all acceptance criteria from spec.md
- [ ] T094 Verify constitution compliance (Container-First, Model Specialization, OpenAI-Compatible API, Resource Efficiency, Developer Experience)
- [ ] T095 Update CLAUDE.md agent context if any dependencies changed during implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (IDE Integration): Can start after Foundational - No dependencies on other stories
  - US2 (WebUI): Can start after Foundational - No dependencies on US1 (independent)
  - US3 (Model Selection): Depends on US1 (router must exist) and US2 (WebUI to enhance) - can start after both
  - US4 (Deployment): Can start after US1, US2, US3 (polishes existing setup)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - IDE)**: Can start after Foundational (Phase 2) - **MVP, no dependencies on other stories**
- **User Story 2 (P2 - WebUI)**: Can start after Foundational (Phase 2) - Independent, can run parallel with US1
- **User Story 3 (P3 - Model Selection)**: Requires US1 router and US2 WebUI to exist - start after both complete
- **User Story 4 (P4 - Deployment)**: Requires US1, US2, US3 - final polish phase

### Within Each User Story

- Router tasks (T015-T025 in US1) should be done sequentially (FastAPI app → auth → routing → endpoints → logging)
- Frontend components (T036-T039 in US2) marked [P] can run in parallel
- Frontend services (T040-T041 in US2) marked [P] can run in parallel
- Documentation tasks marked [P] can run anytime after their feature is implemented

### Parallel Opportunities

- **Setup (Phase 1)**: T004, T005 can run parallel (both documentation)
- **Foundational (Phase 2)**: T010 (volumes) can run parallel with Docker service configs (T007, T008)
- **User Story 1**: T026, T027 (documentation) can run parallel with router implementation
- **User Story 2**: T036-T039 (components), T040-T041 (services), T050 (styling) can run parallel
- **User Story 3**: T059 (ModelSelector), T063 (docs) can run parallel
- **User Story 4**: T074 (diagram) can run anytime after US1 complete
- **Polish (Phase 7)**: T078-T079 (monitoring), T080-T082 (security), T086-T089 (frontend), T090-T092 (docs) can all run parallel

---

## Parallel Example: User Story 1 (IDE Integration)

```bash
# After Foundational phase complete, launch router implementation tasks sequentially:
# (These must be sequential due to dependencies within FastAPI app)

Task T015: Initialize FastAPI app
Task T016: Add auth middleware (depends on T015)
Task T017: Add routing logic (depends on T015, T016)
Tasks T018-T020: Add API endpoints (depend on T015-T017)
Tasks T021-T022: Add health endpoints (depend on T015)
Tasks T023-T025: Add error handling and logging (depend on all above)

# Meanwhile, in parallel, documentation can be written:
Task T026: Create IDE setup guide (no code dependencies)
Task T027: Add troubleshooting section (no code dependencies)
```

---

## Parallel Example: User Story 2 (WebUI)

```bash
# After US2 frontend setup (T031-T035), launch parallel component development:

# Terminal 1 - Components (can all run in parallel, different files)
Task T036: ChatInterface.tsx
Task T037: MessageList.tsx
Task T038: MessageInput.tsx
Task T039: ConnectionStatus.tsx

# Terminal 2 - Services (can run in parallel, different files)
Task T040: api.ts
Task T041: conversationManager.ts

# Terminal 3 - Hooks (sequential within, but can overlap with above)
Task T042: useChat.ts (foundational)
Task T043: useModels.ts (independent)

# Terminal 4 - Styling (can run anytime)
Task T050: index.css
```

---

## Implementation Strategy

### MVP First (User Story 1 Only) - Fastest Path to Value

1. Complete Phase 1: Setup (T001-T005) - ~1 hour
2. Complete Phase 2: Foundational (T006-T014) - ~4 hours
3. Complete Phase 3: User Story 1 (T015-T030) - ~8 hours
4. **STOP and VALIDATE**: Test IDE integration independently with Continue.dev
5. Deploy MVP to GPU machine, share with team for feedback

**Total MVP time**: ~13 hours (1-2 days)
**Deliverable**: Fully functional IDE integration with local models

### Incremental Delivery (Recommended)

1. **Sprint 1**: Setup + Foundational + US1 (IDE Integration) → Deploy MVP (~2 days)
   - Validate: Developers can use Continue.dev with local models
   - Demo: Show code completions without external API calls

2. **Sprint 2**: US2 (WebUI) → Deploy WebUI addition (~2-3 days)
   - Validate: Browser-based chat works independently
   - Demo: Team members can use browser when not in IDE

3. **Sprint 3**: US3 (Model Selection) → Deploy model switching (~1-2 days)
   - Validate: Can switch between Python and general models
   - Demo: Show specialized responses per model type

4. **Sprint 4**: US4 (Deployment Polish) + Phase 7 (Polish) → Production-ready (~2-3 days)
   - Validate: Clean `docker compose up` on fresh machine
   - Demo: Complete system with monitoring and docs

**Total incremental time**: ~7-10 days
**Benefit**: Each sprint delivers independently testable value

### Parallel Team Strategy

With multiple developers (recommended for faster delivery):

1. **Team completes Setup + Foundational together** (~1 day)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (IDE Integration) - T015-T030
   - **Developer B**: User Story 2 (WebUI Setup) - T031-T035, then waits or helps A
3. After US1 complete:
   - **Developer A**: Continue with US3 (Model Selection)
   - **Developer B**: Complete US2 (WebUI Components) - T036-T054
4. After US2 and US3 complete:
   - **Developer A**: US4 (Deployment) - T065-T077
   - **Developer B**: Phase 7 (Polish) - T078-T092 in parallel
5. **Both**: Final validation (T093-T095)

**Total parallel time**: ~4-5 days with 2 developers
**Benefit**: Stories progress simultaneously, frequent integration points

---

## Notes

- [P] tasks = different files, no dependencies - safe to parallelize
- [Story] label maps task to specific user story for traceability and independent testing
- Each user story should be independently completable and testable (validated via "Independent Test" criteria)
- Stop at any checkpoint to validate story independently before proceeding
- Commit after each task or logical group for clean rollback points
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Count Summary

- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 9 tasks
- **Phase 3 (User Story 1 - IDE)**: 16 tasks
- **Phase 4 (User Story 2 - WebUI)**: 24 tasks
- **Phase 5 (User Story 3 - Model Selection)**: 10 tasks
- **Phase 6 (User Story 4 - Deployment)**: 13 tasks
- **Phase 7 (Polish)**: 18 tasks

**Total**: 95 tasks

**Parallelizable**: 28 tasks marked with [P]
**Sequential**: 67 tasks (dependencies within phases)

**MVP (US1 only)**: 30 tasks (Setup + Foundational + US1)
**Full Feature**: 95 tasks (all phases)
