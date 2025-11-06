# Quickstart: Local LLM Service

**Feature**: 001-vllm-webui-service
**Deployment Time**: ~15-20 minutes (excluding model download)
**Difficulty**: Beginner (single command deployment)

## Prerequisites

Before starting, ensure your system has:

- ✅ **Linux OS**: Ubuntu 22.04 LTS or compatible
- ✅ **Docker Engine**: 24.0+ with Docker Compose 2.0+
- ✅ **NVIDIA GPU**: Blackwell 6000 or similar with 96GB VRAM
- ✅ **NVIDIA Drivers**: Version 535+ installed
- ✅ **NVIDIA Container Toolkit**: For GPU passthrough to Docker
- ✅ **Disk Space**: 60-80GB free for model weights
- ✅ **Internet**: For initial model downloads from HuggingFace

### Verify Prerequisites

```bash
# Check Docker version
docker --version  # Should show 24.0+
docker compose version  # Should show 2.0+

# Check NVIDIA driver
nvidia-smi  # Should show GPU with 96GB VRAM

# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
# Should show same output as host nvidia-smi
```

If any checks fail, see [Troubleshooting](#troubleshooting) section.

---

## 5-Minute Setup

### Step 1: Clone Repository (or create from scratch)

```bash
cd ~/projects
git clone https://github.com/your-org/local-llm-service.git
cd local-llm-service
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your preferred editor
nano .env
```

**Minimal `.env` configuration**:

```bash
# API Authentication
API_KEY=sk-local-your-secret-key-here

# Model Configuration
PYTHON_MODEL=TheBloke/deepseek-coder-33B-instruct-AWQ
GENERAL_MODEL=TheBloke/Mistral-7B-v0.1-AWQ

# Service Ports
ROUTER_PORT=8080
WEBUI_PORT=3000
CODER_BACKEND_PORT=8000
GENERAL_BACKEND_PORT=8001
METRICS_PORT=9090

# Performance Tuning
CODER_GPU_MEMORY=0.45
GENERAL_GPU_MEMORY=0.40
CODER_MAX_SEQ=64
GENERAL_MAX_SEQ=128
```

**Generate a secure API key**:

```bash
# Generate random API key
echo "sk-local-$(openssl rand -hex 16)"
```

Copy the generated key to `.env` file.

### Step 3: Start Services

```bash
# Single command to start everything
docker compose up -d

# View logs (Ctrl+C to exit, services keep running)
docker compose logs -f
```

**Expected startup sequence**:
1. `vllm-coder` container starts, begins loading DeepSeek Coder model (~5-8 min)
2. `vllm-general` container starts, begins loading Mistral model (~2-3 min)
3. `vllm-router` starts immediately, waits for backends
4. `webui-frontend` starts immediately

**Progressive availability**: You can start using the general model (~3 min) before the coding model finishes loading (~8 min).

### Step 4: Verify Service Health

```bash
# Check all containers are running
docker compose ps

# Check aggregated health
curl http://localhost:8080/health
# Expected: {"status":"healthy"}

# Check readiness (at least one model loaded)
curl http://localhost:8080/ready
# Expected: {"status":"ready","models":{...}}

# List available models
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer sk-local-your-secret-key-here"
```

### Step 5: Test Inference

**Quick test via curl**:

```bash
# Test Python coding model
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local-your-secret-key-here" \
  -d '{
    "model": "deepseek-coder-33b-instruct",
    "messages": [{"role": "user", "content": "Write a Python function to reverse a string"}],
    "max_tokens": 256,
    "temperature": 0.7
  }'

# Test general model
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local-your-secret-key-here" \
  -d '{
    "model": "mistral-7b-v0.1",
    "messages": [{"role": "user", "content": "What is machine learning?"}],
    "max_tokens": 256
  }'
```

### Step 6: Access WebUI

Open browser to: **http://localhost:3000**

You should see a ChatGPT-like interface. The API key is pre-configured in the frontend environment.

---

## IDE Integration

### VS Code (Continue.dev Extension)

1. **Install Continue extension** from VS Code marketplace

2. **Configure Continue**:
   - Open Command Palette (Ctrl+Shift+P)
   - Search "Continue: Open config.json"
   - Add configuration:

```json
{
  "models": [
    {
      "title": "Local Python Coder",
      "provider": "openai",
      "model": "deepseek-coder-33b-instruct",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "sk-local-your-secret-key-here"
    },
    {
      "title": "Local General",
      "provider": "openai",
      "model": "mistral-7b-v0.1",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "sk-local-your-secret-key-here"
    }
  ]
}
```

3. **Test**: Open any Python file, select code, press Ctrl+L, ask "Explain this code"

### Cursor IDE

1. **Open Settings**: Ctrl+,
2. **Search**: "OpenAI"
3. **Configure**:
   - API Base URL: `http://localhost:8080/v1`
   - API Key: `sk-local-your-secret-key-here`
   - Model: `deepseek-coder-33b-instruct`

### JetBrains (AI Assistant Plugin)

1. **Install AI Assistant plugin**
2. **Settings** → **Tools** → **AI Assistant**
3. **Custom OpenAI Provider**:
   - URL: `http://localhost:8080/v1`
   - API Key: `sk-local-your-secret-key-here`
   - Model: `deepseek-coder-33b-instruct`

### Neovim (copilot.lua)

```lua
-- In your init.lua or copilot.lua config
require('copilot').setup({
  panel = { enabled = false },
  suggestion = {
    enabled = true,
    auto_trigger = true,
  },
  filetypes = {
    python = true,
    javascript = true,
    -- ... other filetypes
  },
  server_opts_overrides = {
    trace = "verbose",
    settings = {
      advanced = {
        inlineSuggestCount = 3,
      },
      openaiUrl = "http://localhost:8080/v1",
      openaiModel = "deepseek-coder-33b-instruct",
      openaiApiKey = "sk-local-your-secret-key-here",
    },
  },
})
```

---

## Service Management

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f vllm-coder
docker compose logs -f vllm-router
docker compose logs -f webui-frontend
```

### Stop Services

```bash
# Stop all (keeps data)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including volumes
docker compose down -v
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart vllm-coder
```

### Update Models

```bash
# Pull newer model versions
docker compose down
docker pull vllm/vllm-openai:latest

# Edit .env to change models
nano .env

# Restart with new configuration
docker compose up -d
```

---

## Monitoring

### GPU Utilization

```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# Or via Docker
docker compose exec vllm-coder nvidia-smi
```

### Prometheus Metrics

Open browser to: **http://localhost:9090/metrics**

Key metrics:
- `vllm:num_requests_running` - Active inference requests
- `vllm:num_requests_waiting` - Queued requests
- `vllm:gpu_cache_usage_perc` - KV cache utilization
- `vllm:time_to_first_token_seconds` - Latency to first token

### Request Logs

```bash
# View request logs with IDs
docker compose logs vllm-router | grep "request_id"

# Filter by model
docker compose logs vllm-coder | grep "deepseek"
```

---

## Troubleshooting

### Model Loading Fails (OOM)

**Symptom**: Container crashes with "CUDA out of memory"

**Solution**:
1. Reduce GPU memory allocation in `.env`:
   ```bash
   CODER_GPU_MEMORY=0.40    # Was 0.45
   GENERAL_GPU_MEMORY=0.35   # Was 0.40
   ```
2. Restart: `docker compose restart`

### API Returns 503 "Model Loading"

**Symptom**: Requests return 503 during startup

**Cause**: Model still loading (expected for 5-10 minutes)

**Solution**: Wait for readiness check to pass:
```bash
# Poll until ready
while ! curl -s http://localhost:8080/ready | grep -q "ready"; do
  echo "Waiting for models..."; sleep 10
done
echo "Service ready!"
```

### Queue Full Errors (503)

**Symptom**: `"Request queue full (100/100)"`

**Cause**: Too many concurrent requests

**Solution**:
1. Increase `max-num-seqs` in `docker-compose.yml`
2. Scale horizontally (add more GPUs/instances)
3. Implement client-side rate limiting

### WebUI Cannot Connect to Backend

**Symptom**: "Connection failed" in browser

**Check**:
```bash
# Verify router is accessible
curl http://localhost:8080/health

# Check WebUI environment
docker compose exec webui-frontend env | grep API
```

**Solution**: Ensure `VITE_API_BASE_URL` in WebUI container matches router URL.

### Token Limit Exceeded

**Symptom**: `"Context window exceeded: X tokens > Y"`

**Solution**:
- Clear conversation history in WebUI (New Chat button)
- Reduce message history length
- System enforces 75% limit automatically

---

## Performance Tuning

### For Higher Throughput

```bash
# In docker-compose.yml, increase batch size:
--max-num-batched-tokens 16384  # Was 8192
--max-num-seqs 128              # Was 64
```

Trade-off: Higher latency per request, more total requests/second.

### For Lower Latency

```bash
# Reduce batch size and sequences
--max-num-batched-tokens 4096
--max-num-seqs 32
```

Trade-off: Faster individual requests, fewer concurrent users.

### For Memory Efficiency

```bash
# Reduce context window
--max-model-len 2048  # Was 4096
```

Trade-off: Less conversation context, lower VRAM usage.

---

## Next Steps

Once service is running:

1. **Configure your IDE** (see [IDE Integration](#ide-integration))
2. **Customize models** in `.env` for your use case
3. **Monitor performance** via Prometheus metrics
4. **Scale horizontally** if needed (multiple GPU support)
5. **Add SSL/TLS** for remote access (nginx reverse proxy)

For implementation details, see:
- [plan.md](./plan.md) - Full technical architecture
- [data-model.md](./data-model.md) - Entity relationships
- [contracts/](./contracts/) - API specifications

---

## Architecture Diagram

```
┌─────────────┐
│  IDE Client │ (VS Code, Cursor, JetBrains)
└──────┬──────┘
       │ HTTP/SSE
       │ Authorization: Bearer sk-local-...
       ▼
┌──────────────────┐
│  vllm-router     │ :8080 (FastAPI)
│  (Port 8080)     │ ├─ /v1/chat/completions
└────────┬─────────┘ ├─ /v1/models
         │           └─ /health, /ready
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌─────────┐
│ vllm-  │ │ vllm-   │
│ coder  │ │ general │
│:8000   │ │:8001    │
└───┬────┘ └────┬────┘
    │           │
    └─────┬─────┘
          │ GPU Access
          ▼
    ┌─────────────┐
    │ Blackwell   │
    │ 6000 GPU    │
    │ 96GB VRAM   │
    └─────────────┘

┌─────────────┐
│  Browser    │
└──────┬──────┘
       │ HTTP
       ▼
┌──────────────────┐
│  webui-frontend  │ :3000 (React)
│  (Port 3000)     │
└──────────────────┘
       │
       └─→ Connects to router :8080
```

---

## Security Notes

- API key is shared across all users (MVP design)
- No HTTPS by default (add nginx for production)
- No per-user authentication (single shared key)
- Logs contain request content (ensure proper access control)
- Model weights stored unencrypted on disk

For production deployment with multiple users, consider:
- Individual API keys with usage tracking
- HTTPS via reverse proxy
- Request rate limiting per key
- Log sanitization (remove sensitive content)
