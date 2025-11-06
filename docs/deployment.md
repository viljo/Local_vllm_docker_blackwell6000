# Deployment Guide

Complete guide for deploying and managing the Local LLM Service.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Starting Services](#starting-services)
5. [Validation](#validation)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Prerequisites

### Hardware Requirements

- **GPU**: NVIDIA GPU with 96GB VRAM (e.g., Blackwell 6000, H100, A100 80GB x2)
- **CPU**: 16+ cores recommended
- **RAM**: 64GB+ system RAM
- **Storage**: 80-100GB free space for model weights

### Software Requirements

- **OS**: Linux (Ubuntu 22.04 LTS recommended)
- **Docker**: Version 24.0 or higher
- **Docker Compose**: Version 2.0 or higher
- **NVIDIA Driver**: Version 535 or higher
- **NVIDIA Container Toolkit**: Latest version

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check NVIDIA driver
nvidia-smi

# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Check available disk space
df -h

# Check available VRAM
nvidia-smi --query-gpu=memory.total --format=csv,noheader
```

All checks should pass before proceeding.

---

## Initial Setup

### 1. Clone Repository

```bash
cd ~/projects
git clone <repository-url>
cd local-llm-service
```

### 2. Review Project Structure

```
local-llm-service/
├── docker-compose.yml          # Service orchestration
├── .env.example               # Configuration template
├── router/                    # FastAPI router service
│   ├── app/
│   │   ├── main.py           # Router application
│   │   └── config.py         # Configuration management
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # React WebUI (Phase 4)
├── docs/                      # Documentation
│   ├── quickstart.md
│   ├── ide-integration.md
│   └── deployment.md (this file)
├── scripts/                   # Utility scripts
│   ├── validate-deployment.sh
│   └── quick-test.sh
└── specs/                     # Design specifications
```

---

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Generate Secure API Key

```bash
# Generate random API key
echo "sk-local-$(openssl rand -hex 16)"
```

Copy the generated key.

### 3. Edit Configuration

```bash
nano .env
```

**Required Configuration:**

```bash
# API Authentication
API_KEY=sk-local-YOUR_GENERATED_KEY_HERE

# Model Configuration
PYTHON_MODEL=TheBloke/deepseek-coder-33B-instruct-AWQ
GENERAL_MODEL=TheBloke/Mistral-7B-v0.1-AWQ

# Service Ports
ROUTER_PORT=8080
CODER_BACKEND_PORT=8000
GENERAL_BACKEND_PORT=8001
WEBUI_PORT=3000

# Performance Tuning (adjust based on your GPU)
CODER_GPU_MEMORY=0.45          # 45% of GPU (43.2GB for 96GB GPU)
GENERAL_GPU_MEMORY=0.40        # 40% of GPU (38.4GB for 96GB GPU)
```

**Optional Tuning:**

```bash
# Context Window
CODER_MAX_MODEL_LEN=4096       # Longer = more context, more VRAM
GENERAL_MAX_MODEL_LEN=4096

# Concurrent Requests
CODER_MAX_SEQ=64               # Max concurrent sequences
GENERAL_MAX_SEQ=128

# Batch Processing
CODER_MAX_BATCHED_TOKENS=8192  # Higher = more throughput, higher latency
GENERAL_MAX_BATCHED_TOKENS=8192

# Logging
LOG_LEVEL=INFO                 # DEBUG for troubleshooting
```

### 4. Adjust GPU Memory Allocation (if needed)

If you have limited VRAM or want to reserve more for system:

```bash
# For 80GB GPU
CODER_GPU_MEMORY=0.40   # ~32GB
GENERAL_GPU_MEMORY=0.35  # ~28GB

# For 96GB GPU (default)
CODER_GPU_MEMORY=0.45   # ~43GB
GENERAL_GPU_MEMORY=0.40  # ~38GB

# For 128GB GPU
CODER_GPU_MEMORY=0.50   # ~64GB
GENERAL_GPU_MEMORY=0.45  # ~58GB
```

---

## Starting Services

### First-Time Startup

```bash
# Pull Docker images (first time only)
docker compose pull

# Start services in detached mode
docker compose up -d

# Follow logs (Ctrl+C to exit, services keep running)
docker compose logs -f
```

**Expected Startup Sequence:**

1. **vllm-coder** starts loading DeepSeek Coder 33B (~5-8 minutes)
2. **vllm-general** starts loading Mistral 7B (~2-3 minutes)
3. **vllm-router** starts immediately, waits for backends
4. **webui-frontend** starts immediately (Phase 4)

**Model Download (First Time Only):**

Models are downloaded from HuggingFace on first startup:
- DeepSeek Coder 33B AWQ: ~25GB download
- Mistral 7B AWQ: ~5GB download
- Total download time: 10-30 minutes (depending on internet speed)

Models are cached in `./models/` directory for subsequent startups.

### Subsequent Startups

```bash
# Start services
docker compose up -d

# Model loading is much faster (1-3 minutes) after first time
```

### Monitoring Startup Progress

```bash
# Check container status
docker compose ps

# Follow coder model logs
docker compose logs -f vllm-coder

# Follow general model logs
docker compose logs -f vllm-general

# Check router logs
docker compose logs -f vllm-router
```

**Look for these log messages:**

```
vllm-coder: Model loaded successfully
vllm-general: Uvicorn running on http://0.0.0.0:8000
vllm-router: Starting router service
```

---

## Validation

### Quick Health Check

```bash
./scripts/quick-test.sh
```

**Expected Output:**
```
Quick Service Test
==================

Checking Docker containers... ✓ Running
Checking router health... ✓ Healthy
Checking model readiness... ✓ Ready

Available models:
  "deepseek-coder-33b-instruct": "ready"
  "mistral-7b-v0.1": "ready"

Service is operational!
```

### Full Validation Suite

```bash
./scripts/validate-deployment.sh
```

This tests:
- ✓ Router health endpoint
- ✓ Router readiness endpoint
- ✓ Authentication (valid and invalid keys)
- ✓ Model listing
- ✓ Chat completions (both models)
- ✓ Streaming responses
- ✓ Error handling (invalid models)

**Expected Result:** All tests pass (8/8)

### Manual API Tests

```bash
# Set your API key
export API_KEY="your-key-from-env-file"

# Test Python coder model
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "deepseek-coder-33b-instruct",
    "messages": [{"role": "user", "content": "Write a Python function to reverse a string"}],
    "max_tokens": 256,
    "temperature": 0.7
  }'

# Test general model
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "mistral-7b-v0.1",
    "messages": [{"role": "user", "content": "What is machine learning?"}],
    "max_tokens": 256
  }'
```

---

## Monitoring

### Real-Time Monitoring

```bash
# GPU utilization
watch -n 1 nvidia-smi

# Container status
docker compose ps

# All service logs
docker compose logs -f

# Specific service logs
docker compose logs -f vllm-coder
docker compose logs -f vllm-general
docker compose logs -f vllm-router
```

### Service Endpoints

- **Health Check**: http://localhost:8080/health
- **Readiness Check**: http://localhost:8080/ready
- **Model List**: http://localhost:8080/v1/models (requires API key)
- **Prometheus Metrics**: http://localhost:9090/metrics (coder)
- **Prometheus Metrics**: http://localhost:9091/metrics (general)

### Key Metrics

**GPU Metrics (nvidia-smi):**
- GPU Utilization: Should be 50-100% during inference
- GPU Memory: ~70-80GB used (for 96GB GPU)
- Temperature: Monitor to ensure adequate cooling

**vLLM Metrics (Prometheus):**
- `vllm:num_requests_running`: Active requests being processed
- `vllm:num_requests_waiting`: Queued requests
- `vllm:gpu_cache_usage_perc`: KV cache utilization
- `vllm:time_to_first_token_seconds`: Latency

**Router Logs:**
- Request IDs for tracing
- Model routing decisions
- Error conditions
- Response times

---

## Troubleshooting

### Container Fails to Start

**Check logs:**
```bash
docker compose logs <service-name>
```

**Common Issues:**

1. **NVIDIA runtime not found**
   ```bash
   # Install NVIDIA Container Toolkit
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

2. **Permission denied on volumes**
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER models/ data/ config/
   ```

3. **Port already in use**
   ```bash
   # Check what's using the port
   sudo lsof -i :8080

   # Change port in .env
   ROUTER_PORT=8081
   ```

### Model Loading Fails (OOM)

**Symptoms:**
- Container exits with code 137
- Logs show "CUDA out of memory"

**Solutions:**

1. **Reduce GPU memory allocation:**
   ```bash
   # In .env
   CODER_GPU_MEMORY=0.40    # Was 0.45
   GENERAL_GPU_MEMORY=0.35  # Was 0.40
   ```

2. **Reduce context window:**
   ```bash
   CODER_MAX_MODEL_LEN=2048  # Was 4096
   ```

3. **Use smaller models:**
   ```bash
   GENERAL_MODEL=TheBloke/Mistral-7B-Instruct-v0.2-AWQ
   ```

### API Returns 503

**Meaning:** Service unavailable

**Possible Causes:**

1. **Models still loading:**
   ```bash
   # Check readiness
   curl http://localhost:8080/ready

   # Wait for models to finish loading (5-10 minutes)
   ```

2. **Backend not responding:**
   ```bash
   # Check backend health
   curl http://localhost:8000/health  # Coder
   curl http://localhost:8001/health  # General
   ```

3. **Queue full:**
   - Wait and retry
   - Increase `max_num_seqs` in docker-compose.yml

### Slow Inference

**Symptoms:** Requests take 10+ seconds

**Causes & Solutions:**

1. **First request (cold start):**
   - Normal: First request allocates KV cache
   - Subsequent requests will be faster

2. **High queue depth:**
   ```bash
   # Check metrics
   curl http://localhost:9090/metrics | grep requests_waiting
   ```

3. **Large context:**
   - Reduce message history
   - Use shorter prompts

4. **GPU contention:**
   - Check if both models running on same GPU
   - Monitor with `nvidia-smi`

### Authentication Failures

**Symptom:** 401 Unauthorized

**Solutions:**

1. **Verify API key:**
   ```bash
   # Check .env file
   grep API_KEY .env
   ```

2. **Restart router:**
   ```bash
   docker compose restart vllm-router
   ```

3. **Check header format:**
   ```bash
   # Correct format
   -H "Authorization: Bearer sk-local-..."
   ```

---

## Maintenance

### Stopping Services

```bash
# Stop all services (keeps containers)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including volumes
docker compose down -v
```

### Restarting Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart vllm-coder
docker compose restart vllm-router
```

### Updating Models

```bash
# Edit .env to change models
nano .env

# Pull new images
docker compose pull

# Restart services
docker compose down
docker compose up -d
```

### Updating Service Code

```bash
# Pull latest code
git pull

# Rebuild router
docker compose build vllm-router

# Restart services
docker compose up -d
```

### Log Management

```bash
# View recent logs
docker compose logs --tail=100

# Save logs to file
docker compose logs > service-logs.txt

# Rotate logs (Docker handles this automatically)
# Configure in /etc/docker/daemon.json:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Backup

**Important directories:**

- `./models/`: Model weights (25-30GB)
- `.env`: Configuration (includes API key)
- `docker-compose.yml`: Service configuration

```bash
# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml

# Models are cached and can be re-downloaded if needed
```

### Performance Tuning

**For higher throughput:**
```yaml
# In docker-compose.yml
--max-num-batched-tokens=16384  # Was 8192
--max-num-seqs=128              # Was 64
```

**For lower latency:**
```yaml
--max-num-batched-tokens=4096
--max-num-seqs=32
```

**For memory efficiency:**
```yaml
--max-model-len=2048  # Was 4096
```

---

## Next Steps

1. **Configure IDE**: See [IDE Integration Guide](ide-integration.md)
2. **Monitor Usage**: Set up Prometheus/Grafana for metrics
3. **Scale Up**: Add more GPU capacity for higher load
4. **Secure**: Add HTTPS via nginx reverse proxy
5. **Customize**: Adjust models and parameters for your use case

For questions or issues, check:
- [Quickstart Guide](quickstart.md)
- [API Documentation](../specs/001-vllm-webui-service/contracts/)
- Project issues on GitHub
