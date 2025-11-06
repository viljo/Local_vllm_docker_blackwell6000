# Local LLM Service

A Docker Compose-based local AI service powered by vLLM, providing OpenAI-compatible APIs for Python coding and general-purpose language models.

## Features

- **Dual-Model Architecture**: Specialized Python coding model (DeepSeek Coder 33B) + general-purpose model (Mistral 7B)
- **OpenAI-Compatible API**: Drop-in replacement for ChatGPT API in IDEs and applications
- **IDE Integration**: Works with VS Code (Continue.dev), Cursor, JetBrains, Neovim
- **Streaming Support**: Server-Sent Events (SSE) for real-time token streaming
- **Single-Command Deployment**: Complete Docker Compose orchestration
- **GPU Optimized**: Efficient VRAM usage via AWQ 4-bit quantization (~68GB total)

## Quick Start

### Prerequisites

- Linux OS (Ubuntu 22.04 LTS or compatible)
- Docker Engine 24.0+ with Docker Compose 2.0+
- NVIDIA GPU with 96GB VRAM (e.g., Blackwell 6000)
- NVIDIA Drivers 535+
- NVIDIA Container Toolkit

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/local-llm-service.git
cd local-llm-service

# Configure environment
cp .env.example .env
nano .env  # Edit API_KEY and other settings

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

### First Request

```bash
# Wait for models to load (~5-10 minutes)
curl http://localhost:8080/ready

# Test Python coding model
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "deepseek-coder-33b-instruct",
    "messages": [{"role": "user", "content": "Write a Python function to reverse a string"}],
    "max_tokens": 256
  }'
```

## Architecture

```
┌─────────────┐
│  IDE Client │ (VS Code, Cursor, JetBrains)
└──────┬──────┘
       │ HTTP/SSE
       ▼
┌──────────────────┐
│  vllm-router     │ :8080 (FastAPI)
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌─────────┐
│ vllm-  │ │ vllm-   │
│ coder  │ │ general │
│:8000   │ │:8001    │
└────────┘ └─────────┘
```

## Documentation

- **[Quickstart Guide](docs/quickstart.md)**: Complete setup and IDE configuration
- **[Specification](specs/001-vllm-webui-service/spec.md)**: Feature requirements and user stories
- **[Implementation Plan](specs/001-vllm-webui-service/plan.md)**: Architecture and design decisions
- **[API Contracts](specs/001-vllm-webui-service/contracts/)**: OpenAPI specifications

## IDE Integration

### VS Code (Continue.dev)

```json
{
  "models": [{
    "title": "Local Python Coder",
    "provider": "openai",
    "model": "deepseek-coder-33b-instruct",
    "apiBase": "http://localhost:8080/v1",
    "apiKey": "YOUR_API_KEY"
  }]
}
```

### Cursor IDE

- Settings → OpenAI
- API Base URL: `http://localhost:8080/v1`
- API Key: `YOUR_API_KEY`
- Model: `deepseek-coder-33b-instruct`

See [quickstart.md](docs/quickstart.md) for JetBrains, Neovim, and other IDE configurations.

## Service Management

```bash
# Stop services
docker compose stop

# Restart services
docker compose restart

# View logs
docker compose logs -f vllm-coder
docker compose logs -f vllm-router

# Remove all containers and volumes
docker compose down -v
```

## Monitoring

- **Health Check**: `http://localhost:8080/health`
- **Readiness Check**: `http://localhost:8080/ready`
- **Prometheus Metrics**: `http://localhost:9090/metrics`
- **GPU Utilization**: `watch -n 1 nvidia-smi`

## Troubleshooting

### Models Won't Load (OOM)

Reduce GPU memory allocation in `.env`:
```bash
CODER_GPU_MEMORY=0.40    # Was 0.45
GENERAL_GPU_MEMORY=0.35   # Was 0.40
```

### API Returns 503

Models are still loading. Check status:
```bash
curl http://localhost:8080/ready
docker compose logs vllm-coder
```

### WebUI Cannot Connect

Verify router is accessible:
```bash
curl http://localhost:8080/health
```

See [quickstart.md](docs/quickstart.md) for more troubleshooting.

## Performance Tuning

Edit `docker-compose.yml` to adjust:
- `--max-num-seqs`: Concurrent request capacity (default: 64/128)
- `--max-num-batched-tokens`: Throughput vs latency trade-off
- `--max-model-len`: Context window size (impacts VRAM)

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines]
