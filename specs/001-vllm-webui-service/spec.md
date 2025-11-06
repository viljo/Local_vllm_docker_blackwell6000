# Feature Specification: Local AI Service with vLLM and WebUI

**Feature Branch**: `001-vllm-webui-service`
**Created**: 2025-10-30
**Status**: Draft
**Input**: User description: "Local AI service with vLLM backend and ChatGPT-like WebUI supporting IDE integration for Python programming with Blackwell 6000 GPU (96GB VRAM)"

## Clarifications

### Session 2025-10-30

- Q: How should API keys be managed for a multi-developer team? → A: Single shared API key for all users
- Q: How many messages should be retained in conversation history before truncation? → A: Dynamic limit based on token count (retain messages up to 75% of model's context window)
- Q: How should the system handle request queue overflow or client disconnections? → A: Queue size limit with rejection (max 100 queued requests, return 503 when full)
- Q: Should the service accept requests before all models are loaded? → A: Progressive availability per model (accept requests for loaded models, return 503 for models still loading)
- Q: How should request logs be managed over time? → A: Log rotation with size limits (retain last 7 days or max 10GB total, whichever comes first)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - IDE Code Assistance (Priority: P1)

A Python developer wants to use their IDE (VS Code, JetBrains, Neovim, or Cursor) to get AI-powered code completions, explanations, and refactoring suggestions using local models instead of external services.

**Why this priority**: This is the primary use case that delivers immediate value. Developers can maintain code privacy, avoid API costs, and get fast responses for daily coding tasks. This MVP delivers the core value proposition.

**Independent Test**: Can be fully tested by configuring an IDE extension (e.g., Continue.dev) to point to `http://localhost:8000/v1`, sending a code completion request, and receiving a streamed response from the Python-specialized model. Success means zero proprietary code leaves the developer's network.

**Acceptance Scenarios**:

1. **Given** the service is running, **When** a developer configures their IDE with the local API endpoint and API key, **Then** the IDE successfully connects and shows "Ready" status
2. **Given** IDE is connected, **When** developer requests code completion for Python, **Then** the system responds with contextually relevant suggestions within 2 seconds
3. **Given** IDE is connected, **When** developer asks to explain a code snippet, **Then** the system provides a clear explanation with correct Python-specific terminology
4. **Given** IDE is connected, **When** developer requests code refactoring, **Then** the system suggests improved code maintaining functionality
5. **Given** multiple developers are using the service, **When** a new request arrives, **Then** the system queues it efficiently and maintains response quality for all users

---

### User Story 2 - Browser Chat Interface (Priority: P2)

A team member wants to interact with the AI through a web browser with a ChatGPT-like interface for general questions, brainstorming, or when not in their IDE.

**Why this priority**: Provides an alternative access method for non-IDE use cases (meetings, documentation, planning) and serves as a fallback when IDE extensions have issues. Complements the primary IDE workflow.

**Independent Test**: Can be fully tested by opening a browser to `http://localhost:3000`, typing a question in the chat interface, and receiving a streamed response. Success means the WebUI provides a complete conversational experience without needing IDE configuration.

**Acceptance Scenarios**:

1. **Given** the service is running, **When** a user opens the WebUI URL in a browser, **Then** they see a chat interface similar to ChatGPT
2. **Given** the WebUI is open, **When** user types a message and presses send, **Then** the response streams in real-time token by token
3. **Given** a conversation is in progress, **When** user sends a follow-up question, **Then** the system maintains conversation context and provides relevant responses
4. **Given** user wants to switch tasks, **When** they start a new conversation, **Then** previous context is cleared and a fresh conversation begins
5. **Given** the WebUI is displaying a response, **When** the user decides they don't need the full answer, **Then** they can stop generation early

---

### User Story 3 - Model Selection (Priority: P3)

A developer wants to choose between a Python-specialized model for coding tasks and a general-purpose model for broader questions, optimizing for task-specific quality.

**Why this priority**: Enhances the experience by allowing users to match model capabilities to their current task, but the service is functional with a single default model. This is a quality-of-life improvement after the core workflows are established.

**Independent Test**: Can be fully tested by sending API requests with different `model` parameters (e.g., "python-coder" vs "general-chat") and verifying responses reflect the expected specialization. Success means model routing works correctly in both IDE and WebUI contexts.

**Acceptance Scenarios**:

1. **Given** multiple models are loaded, **When** user sends a request via IDE specifying the Python model, **Then** the Python-specialized model processes the request
2. **Given** multiple models are loaded, **When** user selects "General Chat" in the WebUI dropdown, **Then** subsequent messages use the general-purpose model
3. **Given** user is switching between models, **When** they change the model selection, **Then** the system routes to the new model without requiring a restart
4. **Given** a model is specified in a request, **When** that model is unavailable, **Then** the system returns a clear error message listing available models

---

### User Story 4 - Single-Command Deployment (Priority: P4)

A team member with no prior Docker experience wants to deploy the entire AI service stack on a machine with an NVIDIA GPU using a single command.

**Why this priority**: Reduces onboarding friction and ensures consistent environments across team members, but this is infrastructure rather than direct user value. Once documented, it's a one-time setup.

**Independent Test**: Can be fully tested by running `docker compose up` on a fresh machine with NVIDIA drivers installed and verifying all services start, health checks pass, and the WebUI becomes accessible. Success means no manual configuration files need editing.

**Acceptance Scenarios**:

1. **Given** Docker and NVIDIA drivers are installed, **When** user runs `docker compose up`, **Then** all services (vLLM backend, WebUI frontend) start without errors
2. **Given** services are starting, **When** user checks logs, **Then** they see clear progress indicators (model loading, server ready, ports bound)
3. **Given** services are running, **When** user navigates to the WebUI URL, **Then** the interface loads and is ready for interaction
4. **Given** services are running, **When** user makes an API request to the health endpoint, **Then** the system returns a healthy status
5. **Given** user wants to stop the service, **When** they run `docker compose down`, **Then** all services shut down cleanly and release GPU resources

---

### Edge Cases

- What happens when GPU memory is exhausted with too many concurrent requests?
  - System should queue up to 100 requests in FIFO order
  - When queue reaches capacity (100 requests), return HTTP 503 "Service Unavailable" with Retry-After header
  - System should never crash due to queue overflow; bounded queue prevents memory exhaustion

- What happens when a model fails to load at startup?
  - System should log clear error messages indicating which model failed and why (missing files, insufficient VRAM)
  - Service should still start and accept requests for successfully loaded models (progressive availability)
  - Failed model should appear in `/v1/models` endpoint with "error" status
  - Requests to failed model should return 503 with descriptive error message

- What happens when the WebUI backend API is unreachable?
  - WebUI should display a user-friendly connection error with troubleshooting steps
  - Should retry connection automatically with exponential backoff

- What happens when an IDE sends malformed API requests?
  - System should return standard OpenAI-compatible error responses with detailed error messages
  - Should log the error for debugging without crashing the service

- What happens when multiple users request different models simultaneously?
  - System should handle concurrent requests to different models efficiently
  - Should maintain separate request queues per model to avoid cross-model blocking

- What happens when conversation context exceeds model's maximum token limit?
  - System should dynamically truncate older messages to stay within 75% of model's context window
  - System should preserve the most recent messages and maintain conversation coherence
  - System should warn the user when approaching the 75% threshold (e.g., at 60-70% usage)

## Requirements *(mandatory)*

### Functional Requirements

#### Backend Service (vLLM)

- **FR-001**: System MUST serve models via OpenAI-compatible REST API endpoints (`/v1/chat/completions`, `/v1/completions`, `/v1/models`)
- **FR-002**: System MUST support streaming responses using Server-Sent Events (SSE) for real-time token delivery
- **FR-003**: System MUST authenticate API requests using a single shared API key configured via environment variable
- **FR-004**: System MUST expose health check endpoints (`/health`, `/ready`) for service monitoring; `/ready` returns 200 when at least one model is loaded and accepting requests
- **FR-005**: System MUST support loading multiple models concurrently within available GPU memory
- **FR-006**: System MUST route requests to the specified model based on the `model` parameter in API requests
- **FR-007**: System MUST expose Prometheus metrics (GPU utilization, memory usage, request latency) for monitoring
- **FR-008**: System MUST log all requests with unique request IDs for traceability
- **FR-008a**: System MUST implement log rotation retaining last 7 days or maximum 10GB total (whichever limit is reached first) to prevent disk exhaustion
- **FR-009**: System MUST queue requests when concurrent load exceeds capacity (maximum 100 queued requests) and process them in FIFO order; when queue is full, return HTTP 503 "Service Unavailable" with Retry-After header
- **FR-009a**: System MUST detect client disconnections and remove corresponding requests from the queue to free capacity for active clients
- **FR-010**: System MUST return standard HTTP error codes with descriptive messages for API failures

#### WebUI Frontend

- **FR-011**: WebUI MUST provide a chat interface where users can send messages and receive responses
- **FR-012**: WebUI MUST display responses with real-time token streaming (text appears as generated)
- **FR-013**: WebUI MUST maintain conversation history for the current session
- **FR-013a**: System MUST dynamically manage conversation context by truncating older messages when token count reaches 75% of the active model's context window
- **FR-014**: WebUI MUST allow users to start a new conversation (clear context)
- **FR-015**: WebUI MUST allow users to stop response generation mid-stream
- **FR-016**: WebUI MUST display model selection dropdown when multiple models are available
- **FR-017**: WebUI MUST communicate with the vLLM backend via the OpenAI-compatible API
- **FR-018**: WebUI MUST display connection status and show errors when backend is unreachable
- **FR-019**: WebUI MUST be responsive and usable on desktop browsers (mobile support optional for MVP)

#### Deployment & Infrastructure

- **FR-020**: System MUST be deployable via `docker compose up` with no manual configuration file editing
- **FR-021**: System MUST pass through NVIDIA GPU(s) to the vLLM container for acceleration
- **FR-022**: System MUST persist model weights in a mounted volume to avoid re-downloading on restarts
- **FR-023**: System MUST use environment variables (`.env` file) for configuration (API keys, ports, model paths)
- **FR-024**: System MUST provide a `.env.example` file documenting all required configuration options
- **FR-025**: System MUST expose clear port mappings (8000 for API, 3000 for WebUI, 9090 for metrics)

#### Model Support

- **FR-026**: System MUST support at least one Python-specialized model (e.g., DeepSeek Coder, CodeLlama, Qwen2.5-Coder)
- **FR-027**: System MUST support at least one general-purpose conversational model (e.g., Mistral, Llama 3, Qwen2.5)
- **FR-028**: System MUST optimize model loading to fit within 96GB VRAM budget (using quantization if needed)
- **FR-029**: System MUST pre-load models at startup to minimize cold-start latency
- **FR-029a**: System MUST accept requests for models that have completed loading while other models are still loading (progressive availability)
- **FR-029b**: System MUST return HTTP 503 "Service Unavailable" for requests targeting models that are still loading, with clear message indicating model is initializing
- **FR-030**: System MUST return the list of available models via the `/v1/models` endpoint, including loading status for each model

### Key Entities

- **Conversation**: A session between a user and the AI, consisting of multiple messages with context maintained across exchanges. Attributes include conversation ID, timestamp, model used, message history, and current token count (dynamically tracked to enforce 75% context window limit).

- **Message**: A single user input or AI response within a conversation. Attributes include role (user/assistant/system), content (text), timestamp, and token count.

- **Model**: An AI language model loaded into the service. Attributes include model name/identifier, specialization (python-coding, general-purpose), memory footprint (VRAM usage), maximum context length, and current status (loading, ready, error). Status transitions: loading → ready (success) or loading → error (failure); service accepts requests only when status is "ready".

- **Request**: An API call from a client (IDE or WebUI) to generate a response. Attributes include request ID, model selected, input messages, streaming preference, timestamp, and authentication token.

- **API Key**: A single shared credential for authenticating all client requests. Attributes include key value (configured in .env file) and rotation capability.

### Assumptions

- NVIDIA drivers (version 535+) and Docker with NVIDIA Container Toolkit are pre-installed on the host system
- Host machine has sufficient disk space for model weights (50-100GB depending on models selected)
- Network connectivity is available for initial model downloads (models cached after first download)
- Users have basic familiarity with Docker commands (`docker compose up/down`)
- IDE extensions (Continue.dev, Cody, etc.) are already installed by users who want IDE integration
- Default configuration will use quantized models (GPTQ/AWQ) if needed to fit both models in 96GB VRAM
- Single shared API key will use simple bearer token authentication (not full OAuth or per-user keys) for MVP simplicity
- WebUI will store conversation history only in browser session storage (not persistent database) for MVP
- Conversation history will be dynamically managed using token counting, maintaining up to 75% of the active model's context window to prevent overflow while maximizing available context
- Request logs will use automatic rotation (7-day retention or 10GB maximum) to prevent disk exhaustion without requiring external log aggregation for MVP

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can configure their IDE and receive first AI response within 5 minutes of starting the service
- **SC-002**: System responds to code completion requests in under 2 seconds for typical requests (50-100 token responses)
- **SC-003**: System handles at least 5 concurrent users making requests without degradation in response quality or significant latency increase
- **SC-004**: Service deployment completes successfully within 10 minutes using `docker compose up` (excluding initial model download time)
- **SC-005**: WebUI loads and is interactive within 3 seconds of navigating to the URL
- **SC-006**: 95% of API requests complete successfully without errors during normal operation
- **SC-007**: System maintains stable GPU memory usage without leaks over extended operation (24+ hours)
- **SC-008**: Streaming responses begin appearing to users within 500ms of request submission
- **SC-009**: Users can switch between Python and general models without service restart or interruption
- **SC-010**: System recovers automatically from transient errors (network blips, temporary GPU issues) without manual intervention
- **SC-011**: First model becomes available and accepts requests within 10 minutes of service startup (progressive availability - no need to wait for all models)
