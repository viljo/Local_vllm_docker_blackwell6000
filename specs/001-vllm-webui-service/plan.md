# Implementation Plan: Local AI Service with vLLM and WebUI

**Branch**: `001-vllm-webui-service` | **Date**: 2025-10-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-vllm-webui-service/spec.md`

## Summary

Build a containerized local AI service using vLLM backend with OpenAI-compatible API and a ChatGPT-like WebUI. Primary use case is IDE integration for Python programming (P1 MVP), with browser-based chat as secondary interface (P2). System leverages Blackwell 6000 GPU (96GB VRAM) to serve specialized Python coding models and general-purpose models concurrently. Complete Docker Compose orchestration enables single-command deployment.

Technical approach: vLLM serves as the inference engine with native OpenAI API compatibility, eliminating need for custom adapter layers. Progressive model loading allows first-loaded model to accept requests immediately. Dynamic context management (75% of model window) and bounded request queues (100 max) prevent resource exhaustion. WebUI communicates via standard OpenAI SDK patterns.

## Technical Context

**Language/Version**: Python 3.11+ (backend/vLLM), TypeScript/JavaScript (WebUI frontend)
**Primary Dependencies**:
- Backend: vLLM 0.5.0+, FastAPI (included in vLLM image), Prometheus client, uvicorn
- Frontend: React 18+ with TypeScript, OpenAI SDK for API client, TanStack Query for state management
**Storage**:
- Local filesystem for model weights (HuggingFace cache format)
- Browser session storage for conversation history (no backend database for MVP)
- JSON structured logs with rotation (7 days / 10GB limit)
**Testing**: pytest for backend contract tests (optional per spec), Vitest for frontend (optional per spec)
**Target Platform**: Linux server (Ubuntu 22.04 LTS) with NVIDIA GPU, Docker 24.0+, NVIDIA Container Toolkit
**Project Type**: Web application (vLLM backend + React frontend, orchestrated by Docker Compose)
**Performance Goals**:
- < 2 seconds for code completion requests (50-100 tokens)
- < 500ms time-to-first-token for streaming responses
- 5+ concurrent users without degradation
- First model ready within 10 minutes of startup
**Constraints**:
- 96GB VRAM budget for all loaded models
- Single shared API key (no per-user auth)
- 100 request queue maximum (bounded to prevent memory exhaustion)
- 75% context window utilization limit (dynamic truncation)
- OpenAI API v1 compatibility requirement (no custom endpoints)
**Scale/Scope**:
- 2 models concurrently loaded (Python coder + general purpose)
- 5-10 concurrent developers (team scale)
- Model sizes: 7B-34B parameters (quantized if needed for VRAM fit)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture
✅ **PASS** - All services containerized with Docker Compose orchestration
- vLLM backend: `vllm/vllm-openai:latest` base image
- WebUI frontend: Node.js Alpine base image
- GPU passthrough via NVIDIA runtime configuration
- Volume mounts for models (`./models`), data (`./data`), config (`./config`)
- Internal Docker network for service discovery

### Principle II: Model Specialization
✅ **PASS** - Dual model strategy with routing
- Python-specialized model: DeepSeek Coder 33B or Qwen2.5-Coder 32B (quantized GPTQ/AWQ if needed)
- General-purpose model: Mistral 7B or Qwen2.5 14B
- vLLM native multi-model support with `model` parameter routing
- Concurrent serving within 96GB VRAM budget

### Principle III: OpenAI-Compatible API (IDE Integration)
✅ **PASS** - Full OpenAI v1 API compatibility
- vLLM provides native `/v1/chat/completions`, `/v1/completions`, `/v1/models` endpoints
- SSE streaming for real-time token delivery
- Single shared API key authentication (bearer token)
- Zero custom adapter code required - drop-in replacement for IDE extensions

### Principle IV: Resource Efficiency
✅ **PASS** - GPU memory and throughput optimization
- vLLM automatic request batching
- Dynamic KV cache management
- Progressive model loading (accept requests per-model as ready)
- Bounded request queue (100 max) prevents memory exhaustion
- Prometheus metrics exposure for GPU utilization, VRAM, latency
- 75% context window limit with dynamic truncation

### Principle V: Developer Experience
✅ **PASS** - Fast setup and clear observability
- `.env` configuration with `.env.example` template
- `/health` and `/ready` endpoints for status checks
- JSON structured logging with request IDs
- Hot reload for frontend development (volume mount in dev mode)
- Quickstart guide with IDE configuration examples (Phase 1 deliverable)

**Gate Result**: ✅ ALL PRINCIPLES SATISFIED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-vllm-webui-service/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (pending)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
├── contracts/           # Phase 1 output (pending)
│   ├── openai-api.yaml  # OpenAI-compatible API contract
│   └── health-api.yaml  # Health check endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Docker Compose orchestration
docker-compose.yml       # Service definitions: vllm-backend, webui-frontend
.env.example             # Configuration template
.env                     # Actual config (gitignored)

# vLLM Backend (no custom code - uses official image with configuration)
# Configuration via environment variables and command-line flags

# WebUI Frontend
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx      # Main chat UI
│   │   ├── MessageList.tsx        # Conversation history display
│   │   ├── MessageInput.tsx       # User input with send/stop controls
│   │   ├── ModelSelector.tsx      # Dropdown for model switching
│   │   └── ConnectionStatus.tsx   # Backend health indicator
│   ├── services/
│   │   ├── api.ts                 # OpenAI SDK client wrapper
│   │   └── conversationManager.ts # Context window management (75% limit)
│   ├── hooks/
│   │   ├── useChat.ts             # Chat state and streaming logic
│   │   └── useModels.ts           # Model list fetching
│   ├── App.tsx                    # Root component
│   └── main.tsx                   # Entry point
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile

# Persistent volumes (host filesystem, mounted into containers)
models/                  # HuggingFace model cache
data/                    # Logs and runtime data
config/                  # Optional configuration overrides

# Documentation (created during implementation)
docs/
└── ide-setup.md         # Per-tool IDE configuration guide
```

**Structure Decision**: Web application pattern selected based on requirement for both programmatic API access (IDE) and browser-based UI (WebUI). Backend uses official vLLM Docker image with no custom application code - pure configuration. Frontend is standalone React SPA communicating via OpenAI-compatible API. Docker Compose orchestrates both services with shared internal network and volume mounts for persistence.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations detected. This section intentionally left empty.
