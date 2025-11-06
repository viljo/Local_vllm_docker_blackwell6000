<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: 0.0.0 → 1.0.0
Created: 2025-10-30

This is the initial constitution for the Local LLM Service project.

Modified Principles:
- NEW: Container-First Architecture
- NEW: Model Specialization
- NEW: OpenAI-Compatible API (IDE Integration)
- NEW: Resource Efficiency
- NEW: Developer Experience

Added Sections:
- Core Principles (5 principles defined)
- Infrastructure Requirements
- Development Standards
- Governance

Templates Requiring Updates:
- ✅ plan-template.md (reviewed - already has Constitution Check section)
- ✅ spec-template.md (reviewed - compatible with principles)
- ✅ tasks-template.md (reviewed - compatible with task structure)

Follow-up TODOs:
- None - all placeholders filled

================================================================================
-->

# Local LLM Service Constitution

## Core Principles

### I. Container-First Architecture

All services MUST be containerized and orchestrated via Docker Compose. This principle ensures:

- Single-command deployment: `docker compose up` starts the entire stack
- Environment isolation: Dependencies managed within containers, not host system
- GPU passthrough: NVIDIA runtime properly configured for vLLM acceleration
- Service discovery: Internal networking for backend-frontend communication
- Volume persistence: Model cache and configuration persist across restarts

**Rationale**: With a Blackwell 6000 GPU (96GB VRAM), containerization ensures reproducible
environments across development and deployment while maintaining clean GPU resource access.
Docker Compose provides declarative infrastructure that any team member can launch identically.

### II. Model Specialization

The service MUST support multiple specialized models optimized for distinct use cases:

- Python programming model: Code-specific LLM (e.g., DeepSeek Coder, CodeLlama, Qwen2.5-Coder)
- General-purpose model: Balanced reasoning and chat (e.g., Mistral, Llama 3, Qwen2.5)
- Model selection API: Clients can route requests to appropriate model endpoint
- Concurrent serving: vLLM supports multiple model instances within available VRAM
- Quantization support: GPTQ/AWQ quantization when needed for larger models

**Rationale**: Python programmers need code-aware models that understand syntax, libraries, and
patterns, while general chat requires broader reasoning. Specialization maximizes quality per use
case within the 96GB VRAM budget.

### III. OpenAI-Compatible API (IDE Integration)

All model interactions MUST go through OpenAI-compatible REST APIs to enable seamless IDE integration:

- **Standard ChatGPT API**: Full compatibility with OpenAI API spec (`/v1/chat/completions`, `/v1/completions`, `/v1/models`)
- **IDE tool support**: Drop-in replacement for ChatGPT in VS Code extensions (Continue.dev, Cody, GitHub Copilot alternatives)
- **Direct IDE usage**: Developers configure their IDE to point to local service instead of OpenAI
- **API key authentication**: Environment-configured keys for multi-user access control
- **Streaming responses**: SSE (Server-Sent Events) for real-time token streaming in IDE chat
- **Model switching**: IDE can select between Python-focused and general models via `model` parameter

**Rationale**: The primary use case is developers using their existing IDE workflows (inline completion,
chat panels, code explanation) with local models. OpenAI API compatibility means zero code changes
in IDE extensions—just update the base URL and API key. This enables private, fast, cost-free
coding assistance without sending proprietary code to external services.

**IDE Configuration Example**:
```json
{
  "openai.apiBase": "http://localhost:8000/v1",
  "openai.apiKey": "sk-local-dev-key",
  "openai.model": "deepseek-coder-33b"
}
```

### IV. Resource Efficiency

Infrastructure MUST optimize for GPU memory and inference throughput:

- vLLM tensor parallelism: Leverage multi-GPU when available or plan for future scaling
- KV cache management: Tune `max_num_seqs` and `max_model_len` per model requirements
- Batch processing: vLLM automatically batches concurrent requests
- Model warmup: Pre-load models at startup to avoid cold-start latency
- Monitoring: Expose Prometheus metrics for GPU utilization, memory, request latency

**Rationale**: The Blackwell 6000's 96GB VRAM is substantial but finite. Efficient scheduling
maximizes concurrent users and request throughput. Monitoring prevents resource exhaustion and
enables data-driven optimization.

### V. Developer Experience

The system MUST prioritize ease of setup, debugging, and iteration:

- Environment files: `.env` for configuration (API keys, model paths, ports)
- Health endpoints: `/health` and `/ready` for service status verification
- Structured logging: JSON logs with request IDs for traceability
- Hot reload: Frontend code changes reflected without full rebuild
- Documentation: README with quickstart, IDE setup guide, architecture diagram, troubleshooting

**Rationale**: Python programmers value fast iteration cycles and clear error messages. A
well-documented, observable system reduces onboarding friction and debugging time. Clear IDE
setup instructions ensure developers can connect their tools within minutes.

## Infrastructure Requirements

### Deployment Stack

- Docker Engine 24.0+ with NVIDIA Container Toolkit
- Docker Compose 2.0+ for multi-container orchestration
- NVIDIA Driver 535+ (for Blackwell 6000 support)
- Host OS: Linux (Ubuntu 22.04 LTS recommended)

### Service Components

1. **vLLM Backend (Primary)**
   - Base image: `vllm/vllm-openai:latest` (includes CUDA, PyTorch, vLLM)
   - GPU access: All GPUs passed through (`device: 0` or `count: all`)
   - Ports: 8000 (API), 9090 (metrics)
   - Volumes: Model cache mounted from host
   - API compliance: Full OpenAI v1 API compatibility for IDE tools

2. **WebUI Frontend**
   - Technology: Modern web framework (Next.js, React, Vue, or Svelte)
   - Base image: Node.js Alpine for minimal footprint
   - Ports: 3000 (HTTP), reverse proxy optional
   - Environment: Backend API URL injected at runtime
   - Purpose: ChatGPT-like interface for browser-based interaction

3. **Reverse Proxy (Optional)**
   - Technology: Nginx or Traefik for SSL termination and routing
   - Purpose: Single HTTPS entry point for production deployments
   - Use case: Remote IDE access over network with TLS

### Persistent Storage

- `./models:/models` - Downloaded model weights (read-only in container)
- `./data:/data` - User data, conversation history, API keys database
- `./config:/config` - Service configuration overrides

### IDE Compatibility

The service MUST support these common IDE integrations:

- **VS Code**: Continue, Cody, Tabnine, CodeGPT extensions
- **JetBrains**: AI Assistant, GitHub Copilot alternatives
- **Neovim**: copilot.lua, cmp-ai, neural plugins
- **Cursor**: Direct OpenAI API configuration
- **CLI tools**: Any tool using OpenAI Python/Node.js SDKs

Configuration requirement: Base URL + API key only (no custom adapters needed).

## Development Standards

### Configuration Management

- All secrets in `.env` (never committed; `.env.example` provided)
- Service settings in `docker-compose.yml` (ports, resources, networks)
- Model settings in vLLM command flags (max tokens, temperature defaults)
- Frontend settings in environment variables (API endpoint, feature flags)
- IDE setup guide in `docs/ide-setup.md` with per-tool configuration snippets

### Testing Requirements

Testing is OPTIONAL unless explicitly required by feature specifications. When tests are needed:

- **Integration tests**: Verify API endpoints return expected formats
- **Contract tests**: Validate OpenAI API compatibility (e.g., `/v1/chat/completions` schema)
- **IDE compatibility tests**: Verify common IDE tools can connect and receive responses
- **Performance tests**: Measure tokens/second, concurrent request capacity
- Framework: pytest for backend, Jest/Vitest for frontend

### Code Quality

- Python: Black formatter, flake8 linter, type hints (mypy)
- JavaScript/TypeScript: Prettier formatter, ESLint, TypeScript strict mode
- Dockerfile: Hadolint for best practices
- Compose: YAML linting, schema validation

### Version Control

- Semantic versioning: MAJOR.MINOR.PATCH
  - MAJOR: Breaking API changes, incompatible model format changes
  - MINOR: New models added, backward-compatible features
  - PATCH: Bug fixes, documentation, configuration improvements
- Git branches: `main` (stable), feature branches per specification
- Commit style: Conventional Commits (e.g., `feat: add model switching endpoint`)

## Governance

### Constitution Authority

This constitution supersedes all other development practices and coding conventions. All design
decisions, pull requests, and feature specifications MUST comply with the principles defined above.

### Amendment Process

1. Proposed changes documented in specification with rationale
2. Principles reviewed for impact on existing features
3. Version incremented following semantic versioning rules:
   - **MAJOR**: Principle removed or redefined (breaks existing assumptions)
   - **MINOR**: New principle added or existing principle materially expanded
   - **PATCH**: Clarifications, wording improvements, examples added
4. All dependent templates updated (plan, spec, tasks)
5. Migration plan documented if changes affect existing code

### Compliance Review

- All specifications MUST include a "Constitution Check" section mapping requirements to principles
- Pull requests rejected if they violate principles without documented justification
- Complexity introduced beyond principles MUST be justified in "Complexity Tracking" table

### Deviation Justification

If a feature cannot comply with a principle, the specification MUST include:

- Which principle(s) are violated
- Why the feature requires deviation
- What simpler alternatives were considered and rejected
- Compensating controls or temporary exceptions

Example: "Model served outside Docker for benchmarking (violates Container-First) - needed for
hardware profiling; production deployment still containerized."

### Related Documentation

- Runtime development guidance: Refer to feature-specific `quickstart.md` in `specs/[###-feature]/`
- Template usage: See `.specify/templates/` for spec, plan, tasks, and checklist workflows
- Command reference: See `.claude/commands/speckit.*.md` for automation workflows
- IDE setup: See `docs/ide-setup.md` for per-tool configuration (created during implementation)

**Version**: 1.0.0 | **Ratified**: 2025-10-30 | **Last Amended**: 2025-10-30
