# Deployment Commands: Ready-to-Copy

All commands are ready to copy and paste. Adjust paths and ports as needed.

---

## Step 1: Verify Prerequisites

### Check GPU Memory
```bash
nvidia-smi
```

Expected output should show ~96GB total memory. If you see less, you may need to adjust model selection.

### Check CUDA Availability
```bash
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.0f} GB')"
```

### Verify Python Version
```bash
python --version  # Should be 3.8 or higher
```

---

## Step 2: Install vLLM with Quantization Support

### Basic Installation
```bash
pip install vllm
```

### Installation with Optional Dependencies (Recommended)
```bash
pip install vllm[torch]
pip install transformers
```

### Verify Installation
```bash
python -c "from vllm import LLM; print('vLLM installed successfully')"
```

### Check vLLM Version
```bash
python -c "import vllm; print(f'vLLM version: {vllm.__version__}')"
```

---

## Step 3: Download Models

### Option A: Using HuggingFace CLI (Recommended)

#### Install HuggingFace CLI
```bash
pip install huggingface-hub
```

#### Download DeepSeek Coder 33B AWQ
```bash
huggingface-cli download TheBloke/deepseek-coder-33B-instruct-AWQ
```

#### Download Mistral 7B AWQ
```bash
huggingface-cli download TheBloke/Mistral-7B-v0.1-AWQ
```

#### Or if using Qwen models:
```bash
huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
huggingface-cli download Qwen/Qwen2.5-7B-Instruct
```

### Option B: Using Python Transformers

```python
from huggingface_hub import snapshot_download

# Download DeepSeek Coder
snapshot_download('TheBloke/deepseek-coder-33B-instruct-AWQ')

# Download Mistral 7B
snapshot_download('TheBloke/Mistral-7B-v0.1-AWQ')

print("Models downloaded successfully")
```

### Verify Downloaded Models
```bash
# List downloaded model sizes
du -sh ~/.cache/huggingface/hub/models--*/ | sort -h
```

---

## Step 4: Start vLLM Servers

### Option 1: Terminal 1 - DeepSeek Coder 33B

```bash
python -m vllm.entrypoints.api_server \
  --model TheBloke/deepseek-coder-33B-instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.88 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 128 \
  --dtype float16 \
  --port 8000
```

### Option 2: Terminal 2 - Mistral 7B

```bash
python -m vllm.entrypoints.api_server \
  --model TheBloke/Mistral-7B-v0.1-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.88 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 128 \
  --dtype float16 \
  --port 8001
```

### If Using Qwen Models Instead:

**Terminal 1 - Qwen2.5-Coder 32B**
```bash
python -m vllm.entrypoints.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.88 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 128 \
  --dtype float16 \
  --port 8000
```

**Terminal 2 - Qwen2.5 7B**
```bash
python -m vllm.entrypoints.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --gpu-memory-utilization 0.88 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 128 \
  --dtype float16 \
  --port 8001
```

---

## Step 5: Test Servers

### Test Server 1 (Port 8000)

```bash
curl http://localhost:8000/v1/models
```

Expected output: JSON listing the model information

### Test Server 2 (Port 8001)

```bash
curl http://localhost:8001/v1/models
```

### Basic Completion Test (DeepSeek Coder)

```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TheBloke/deepseek-coder-33B-instruct-AWQ",
    "prompt": "def fibonacci(n):",
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

### Basic Completion Test (Mistral 7B)

```bash
curl -X POST http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TheBloke/Mistral-7B-v0.1-AWQ",
    "prompt": "The capital of France is",
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

---

## Step 6: Python Client Testing

### Install Python Client
```bash
pip install openai  # vLLM provides OpenAI-compatible API
```

### Python Test Script: Basic Inference

```python
from openai import OpenAI

# Initialize clients for both models
coder_client = OpenAI(api_key="sk-placeholder", base_url="http://localhost:8000/v1")
general_client = OpenAI(api_key="sk-placeholder", base_url="http://localhost:8001/v1")

# Test coder model
print("=== Testing DeepSeek Coder 33B ===")
code_response = coder_client.completions.create(
    model="TheBloke/deepseek-coder-33B-instruct-AWQ",
    prompt="def quicksort(arr):",
    max_tokens=150,
    temperature=0.7
)
print(code_response.choices[0].text)

# Test general model
print("\n=== Testing Mistral 7B ===")
general_response = general_client.completions.create(
    model="TheBloke/Mistral-7B-v0.1-AWQ",
    prompt="Explain quantum computing in simple terms:",
    max_tokens=150,
    temperature=0.7
)
print(general_response.choices[0].text)
```

### Python Test Script: Concurrent Requests

```python
import asyncio
from openai import AsyncOpenAI

async def test_concurrent_inference():
    coder_client = AsyncOpenAI(api_key="sk-placeholder", base_url="http://localhost:8000/v1")
    general_client = AsyncOpenAI(api_key="sk-placeholder", base_url="http://localhost:8001/v1")

    # Create concurrent requests
    coder_task = coder_client.completions.create(
        model="TheBloke/deepseek-coder-33B-instruct-AWQ",
        prompt="def merge_sort(arr):",
        max_tokens=100
    )

    general_task = general_client.completions.create(
        model="TheBloke/Mistral-7B-v0.1-AWQ",
        prompt="What is machine learning?",
        max_tokens=100
    )

    # Run concurrently
    coder_result, general_result = await asyncio.gather(coder_task, general_task)

    print("Coder response:", coder_result.choices[0].text)
    print("General response:", general_result.choices[0].text)

# Run async test
asyncio.run(test_concurrent_inference())
```

---

## Step 7: Monitor GPU Memory

### Real-time Monitoring (Terminal 3)

```bash
watch -n 1 nvidia-smi
```

Or for continuous output:

```bash
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv,noheader -l 1
```

### Memory Usage in Python

```python
import torch

def print_gpu_memory():
    allocated = torch.cuda.memory_allocated() / 1e9
    reserved = torch.cuda.memory_reserved() / 1e9
    total = torch.cuda.get_device_properties(0).total_memory / 1e9

    print(f"GPU Memory Allocated: {allocated:.2f} GB")
    print(f"GPU Memory Reserved:  {reserved:.2f} GB")
    print(f"GPU Memory Total:     {total:.2f} GB")
    print(f"GPU Memory Free:      {total - allocated:.2f} GB")

# Call periodically
while True:
    print_gpu_memory()
    time.sleep(5)
```

---

## Step 8: Troubleshooting Commands

### Check for OOM Errors
```bash
# Search recent logs for CUDA out of memory
dmesg | grep -i "out of memory" | tail -20
```

### Clear GPU Memory
```bash
# Kill all Python processes
pkill -9 python

# Clear GPU cache (if needed)
nvidia-smi --gpu-reset
```

### Reduce Memory Usage (if getting OOM)

Modify the vLLM server launch command with tighter settings:

```bash
python -m vllm.entrypoints.api_server \
  --model TheBloke/deepseek-coder-33B-instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.85 \
  --max-num-batched-tokens 6144 \
  --max-num-seqs 64 \
  --dtype float16 \
  --port 8000
```

Parameters to reduce if tight on memory:
- `--gpu-memory-utilization`: Reduce from 0.88 to 0.80
- `--max-num-batched-tokens`: Reduce from 8192 to 4096
- `--max-num-seqs`: Reduce from 128 to 32

---

## Step 9: Benchmark Performance

### Simple Latency Test

```python
import time
from openai import OpenAI

client = OpenAI(api_key="sk-placeholder", base_url="http://localhost:8000/v1")

# Warmup
client.completions.create(
    model="TheBloke/deepseek-coder-33B-instruct-AWQ",
    prompt="test",
    max_tokens=10
)

# Benchmark
prompts = [
    "def fibonacci(n):",
    "def merge_sort(arr):",
    "def binary_search(arr, target):",
]

for prompt in prompts:
    start = time.time()
    response = client.completions.create(
        model="TheBloke/deepseek-coder-33B-instruct-AWQ",
        prompt=prompt,
        max_tokens=100,
        temperature=0.7
    )
    elapsed = time.time() - start
    tokens = response.usage.completion_tokens
    tps = tokens / elapsed

    print(f"Prompt: {prompt[:20]}... | Time: {elapsed:.2f}s | Tokens: {tokens} | TPS: {tps:.1f}")
```

### Throughput Test (Concurrent Requests)

```python
import asyncio
import time
from openai import AsyncOpenAI

async def benchmark_throughput():
    client = AsyncOpenAI(api_key="sk-placeholder", base_url="http://localhost:8000/v1")

    prompts = ["def fibonacci(n):" for _ in range(10)]

    start = time.time()

    tasks = [
        client.completions.create(
            model="TheBloke/deepseek-coder-33B-instruct-AWQ",
            prompt=prompt,
            max_tokens=50
        )
        for prompt in prompts
    ]

    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start
    total_tokens = sum(r.usage.completion_tokens for r in results)

    print(f"Processed {len(results)} requests in {elapsed:.2f}s")
    print(f"Total tokens: {total_tokens}")
    print(f"Throughput: {total_tokens/elapsed:.1f} tokens/sec")

asyncio.run(benchmark_throughput())
```

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Check GPU | `nvidia-smi` |
| Install vLLM | `pip install vllm` |
| Download models | `huggingface-cli download <model-name>` |
| Start DeepSeek | `python -m vllm.entrypoints.api_server --model TheBloke/deepseek-coder-33B-instruct-AWQ --quantization awq --port 8000` |
| Start Mistral | `python -m vllm.entrypoints.api_server --model TheBloke/Mistral-7B-v0.1-AWQ --quantization awq --port 8001` |
| Test endpoint | `curl http://localhost:8000/v1/models` |
| Kill servers | `pkill -f "api_server"` |
| Monitor memory | `watch -n 1 nvidia-smi` |
| Run Python test | `python test_inference.py` |

---

## Production Considerations

### Use a Process Manager

#### Option 1: systemd Service File

Create `/etc/systemd/system/vllm-coder.service`:
```ini
[Unit]
Description=vLLM Coder Server
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>
ExecStart=/usr/bin/python -m vllm.entrypoints.api_server \
  --model TheBloke/deepseek-coder-33B-instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.88 \
  --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl start vllm-coder
sudo systemctl enable vllm-coder
```

#### Option 2: Using supervisor

```bash
pip install supervisor
```

Create `/etc/supervisor/conf.d/vllm.conf`:
```ini
[program:vllm_coder]
command=python -m vllm.entrypoints.api_server --model TheBloke/deepseek-coder-33B-instruct-AWQ --quantization awq --port 8000
autostart=true
autorestart=true
stderr_logfile=/var/log/vllm_coder.err.log
stdout_logfile=/var/log/vllm_coder.out.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start vllm_coder
```

### Add a Load Balancer (Optional)

If you need HTTP load balancing between the two servers, use nginx:

```nginx
upstream vllm_coder {
    server localhost:8000;
}

upstream vllm_general {
    server localhost:8001;
}

server {
    listen 8080;
    server_name _;

    location /coder/ {
        proxy_pass http://vllm_coder/;
    }

    location /general/ {
        proxy_pass http://vllm_general/;
    }
}
```

Then start nginx and access via http://localhost:8080/coder/ and http://localhost:8080/general/

---

## Cleanup & Shutdown

### Stop vLLM Servers
```bash
# Kill all Python vLLM processes
pkill -f "api_server"

# Or more selective:
lsof -i :8000 -i :8001  # See what's running
kill -9 <PID>            # Kill specific process
```

### Remove Downloaded Models
```bash
# Free up disk space (models are cached at):
rm -rf ~/.cache/huggingface/hub/

# Or selective removal:
rm -rf ~/.cache/huggingface/hub/models--TheBloke*
```

### Full System Reset
```bash
# Kill everything
pkill -9 python

# Clear GPU memory
nvidia-smi --gpu-reset

# Clear cache
rm -rf ~/.cache/huggingface/hub/
```

---

## Summary

1. **Verify GPU:** `nvidia-smi`
2. **Install vLLM:** `pip install vllm`
3. **Download models:** `huggingface-cli download <model>`
4. **Start servers:** Run two terminal instances with the appropriate launch commands
5. **Test:** Use curl or Python clients to verify
6. **Monitor:** Use `watch nvidia-smi` to monitor memory
7. **Deploy:** Use systemd or supervisor for production

All commands above are copy-paste ready. Adjust paths, ports, and model names as needed for your setup.

