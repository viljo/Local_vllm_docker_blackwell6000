# VRAM Calculation Reference & Quick Setup Guide

## Quick VRAM Calculation Formula

### For Model Weights Only
```
VRAM (GB) = (Parameters in Billions × Bytes per Parameter) / (1024³)

For FP16/BF16:    Bytes per parameter = 2
For 4-bit (GPTQ): Bytes per parameter = 0.5
For 4-bit (AWQ):  Bytes per parameter ≈ 0.5-0.6
For 8-bit:        Bytes per parameter = 1
```

### For Total VRAM with vLLM (Including KV Cache)
```
Total VRAM = Model Weights + KV Cache + Inference Overhead

Approximate formula:
- Small models (7B):   Model Size × 3-4x
- Medium models (33B): Model Size × 2.5-3x
- With batching:       Add 10-20% more for per-request overhead

Example (DeepSeek Coder 33B AWQ):
- Model: 18 GB (0.5 bytes × 33B parameters)
- KV Cache: ~25-30 GB (depends on max_tokens, batch_size)
- Total: ~50 GB
```

---

## Model-Specific VRAM Estimates

### 33B Models (DeepSeek Coder, Qwen2.5-Coder)
```
FP16:
  Model Weights:       66 GB
  + KV Cache (max seq): 8-10 GB
  + Batching overhead:  2-5 GB
  Total:               76-81 GB (per model)

4-bit AWQ:
  Model Weights:       18-20 GB
  + KV Cache (max seq): 25-30 GB
  + Batching overhead:  2-5 GB
  Total:               45-55 GB (per model)

4-bit GPTQ:
  Model Weights:       15-16 GB
  + KV Cache (max seq): 28-35 GB  (higher due to vLLM overhead)
  + Batching overhead:  2-5 GB
  Total:               45-56 GB (per model)
```

### 7B Models (Mistral, Qwen2.5)
```
FP16:
  Model Weights:       14 GB
  + KV Cache (max seq): 8-10 GB
  + Batching overhead:  2-4 GB
  Total:               24-28 GB (per model)

4-bit AWQ:
  Model Weights:       3.5-4 GB
  + KV Cache (max seq): 14-18 GB
  + Batching overhead:  1-3 GB
  Total:               18-25 GB (per model)
```

### 14B Models (Qwen2.5)
```
FP16:
  Model Weights:       28 GB
  + KV Cache (max seq): 12-15 GB
  + Batching overhead:  2-4 GB
  Total:               42-47 GB (per model)

4-bit AWQ:
  Model Weights:       7-8 GB
  + KV Cache (max seq): 18-24 GB
  + Batching overhead:  2-4 GB
  Total:               27-36 GB (per model)
```

---

## 96GB GPU Budget Scenarios

### Scenario 1: Best Performance & Safety (Recommended)
```
DeepSeek Coder 33B AWQ: 50 GB
Mistral 7B AWQ:         20 GB
Headroom (26 GB):       Continuous batching, emergency buffer
─────────────────────────────────
Total:                  96 GB ✓✓✓
Workload:               8+ concurrent requests per model
Accuracy:               98.9% (vs FP16)
```

### Scenario 2: Larger General Model
```
DeepSeek Coder 33B AWQ: 50 GB
Qwen2.5 14B AWQ:        30 GB
Headroom (16 GB):       Limited batching
─────────────────────────────────
Total:                  96 GB ✓✓
Workload:               4-6 concurrent requests
Accuracy:               98.9%
Note:                   Tight memory, reduce max_batched_tokens
```

### Scenario 3: Alternative Qwen Models
```
Qwen2.5-Coder 32B AWQ:  50 GB
Qwen2.5 7B:             18 GB
Headroom (28 GB):       Good batching capacity
─────────────────────────────────
Total:                  96 GB ✓✓✓
Workload:               8-10 concurrent requests
Accuracy:               98.9%
Advantage:              Consistent Qwen family
```

### What DOESN'T Work: FP16
```
DeepSeek Coder 33B FP16: 75 GB
Mistral 7B FP16:         25 GB
─────────────────────────────────
Total:                  100 GB ✗✗✗
Result:                 Doesn't fit, OOM errors
```

### What DOESN'T Work: 8-bit on Both
```
DeepSeek Coder 33B 8-bit: 60 GB
Mistral 7B 8-bit:         28 GB
─────────────────────────────────
Total:                   88 GB ✓
Headroom:                 8 GB  (inadequate for batching)
Result:                   High OOM risk, no batching
```

---

## VRAM Tuning Parameters for vLLM

### Memory Utilization
```bash
# Default: 90% of GPU memory
--gpu-memory-utilization 0.90

# For concurrent models: reduce to 85%
--gpu-memory-utilization 0.85

# Conservative: 80% (max safety)
--gpu-memory-utilization 0.80

# Calculation: Total_VRAM × gpu-memory-utilization
# Example: 96GB × 0.90 = 86.4GB available (9.6GB system reserve)
```

### Token Batching
```bash
# Controls KV cache size per batch
--max-num-batched-tokens <N>

# Default recommendations:
# 7B models:   8192-16384 tokens
# 33B models:  6144-12288 tokens
# Both:        8192 tokens (balanced)

# For tight memory (concurrent): 6144 tokens
--max-num-batched-tokens 6144

# KV cache per token ≈ 2 × hidden_size × 2 (key+value)
# For 33B: ~44 GB memory for max_tokens=4096 + batching
```

### Max Sequences (Batch Size)
```bash
# Number of parallel sequences/requests
--max-num-seqs 256  # Default

# Reduce to lower KV cache:
--max-num-seqs 128  # ~50% less KV memory
--max-num-seqs 64   # ~75% less KV memory

# Trade-off: lower throughput, less memory needed
```

### Context Length
```bash
# Don't specify max_position_embeddings if not needed
# Shorter context = smaller KV cache

# Example: 4096 tokens vs 8192 tokens
# KV cache difference: ~50% larger at 8192
```

---

## vLLM Multi-Model Setup Examples

### Example 1: Single GPU, Both Models (Recommended)
```python
# Launch as two separate processes on same GPU
# Process 1: DeepSeek Coder 33B
import subprocess

process1 = subprocess.Popen([
    'python', '-m', 'vllm.entrypoints.api_server',
    '--model', 'TheBloke/deepseek-coder-33B-instruct-AWQ',
    '--quantization', 'awq',
    '--gpu-memory-utilization', '0.88',
    '--max-num-batched-tokens', '8192',
    '--max-num-seqs', '128',
    '--port', '8000'
])

# Process 2: Mistral 7B
process2 = subprocess.Popen([
    'python', '-m', 'vllm.entrypoints.api_server',
    '--model', 'TheBloke/Mistral-7B-v0.1-AWQ',
    '--quantization', 'awq',
    '--gpu-memory-utilization', '0.88',
    '--max-num-batched-tokens', '8192',
    '--max-num-seqs', '128',
    '--port', '8001'
])
```

### Example 2: Memory-Constrained Configuration
```bash
# If getting OOM errors, reduce parameters:

python -m vllm.entrypoints.api_server \
  --model TheBloke/deepseek-coder-33B-instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.85 \
  --max-num-batched-tokens 6144 \
  --max-num-seqs 64 \
  --cpu-offload-gb 2 \
  --port 8000
```

### Example 3: Load Balancing Between Models
```python
# Route requests to appropriate model based on task
import requests

def call_coder_model(prompt: str):
    response = requests.post(
        'http://localhost:8000/v1/completions',
        json={
            'model': 'deepseek-coder-33b-instruct-awq',
            'prompt': prompt,
            'max_tokens': 512
        }
    )
    return response.json()

def call_general_model(prompt: str):
    response = requests.post(
        'http://localhost:8001/v1/completions',
        json={
            'model': 'mistral-7b-v0.1-awq',
            'prompt': prompt,
            'max_tokens': 512
        }
    )
    return response.json()

# Route based on task type
if 'code' in prompt.lower():
    result = call_coder_model(prompt)
else:
    result = call_general_model(prompt)
```

---

## Memory Monitoring During Runtime

### Check GPU Memory Usage
```bash
# Real-time monitoring
watch -n 1 nvidia-smi

# In Python
import torch
print(f"GPU Memory Used: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
print(f"GPU Memory Reserved: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
```

### vLLM Memory Diagnostic
```bash
# Check vLLM's memory stats endpoint (if enabled)
curl http://localhost:8000/stats

# Monitor logs for memory warnings
# Look for: "WARNING: GPU is running out of memory"
```

---

## Quantization Method Decision Tree

```
Do you have 96GB VRAM?
├─ Yes → Need 2 models concurrently?
│  ├─ Yes → Use 4-bit quantization
│  │  ├─ Memory is tight? → Use AWQ
│  │  └─ Need max accuracy? → Use 8-bit (but review VRAM)
│  └─ No → Can use FP16 for single model
└─ No → Use 4-bit quantization (required)

Is vLLM your inference engine?
├─ Yes → AWQ is slightly better (lower overhead)
└─ No → GPTQ might be more compatible elsewhere

Is code generation accuracy critical?
├─ Yes → Both AWQ & GPTQ are equivalent (98.9% recovery)
└─ No → AWQ recommended (better general language)
```

---

## Pre-Download Command Examples

### Download Models Efficiently
```bash
# Using HuggingFace CLI
huggingface-cli download TheBloke/deepseek-coder-33B-instruct-AWQ

# Using Python transformers
from huggingface_hub import snapshot_download
snapshot_download('TheBloke/deepseek-coder-33B-instruct-AWQ')

# With cache directory
HF_HOME=/path/to/cache huggingface-cli download TheBloke/deepseek-coder-33B-instruct-AWQ
```

### Verify Downloaded Models
```bash
# Check file sizes to estimate actual VRAM
du -sh ~/.cache/huggingface/hub/models--TheBloke*

# For 33B 4-bit model: expect ~15-20 GB on disk
# For 7B 4-bit model: expect ~3-5 GB on disk
```

---

## Troubleshooting VRAM Issues

### Error: "CUDA out of memory"
```
Solution 1: Reduce --gpu-memory-utilization to 0.80
Solution 2: Reduce --max-num-batched-tokens to 4096
Solution 3: Reduce --max-num-seqs to 32
Solution 4: Increase --cpu-offload-gb for CPU fallback
```

### Error: "Model too large to load"
```
Check:
  1. Verify using quantized version (not FP16)
  2. Confirm GPU memory: nvidia-smi
  3. Close other GPU processes: nvidia-smi | grep PID
  4. Restart GPU: 'sudo systemctl restart nvidia-persistence-daemon'
```

### Memory Leaks Over Time
```
Monitor:
  1. Watch memory growth: nvidia-smi -l 1
  2. Check for memory fragmentation
  3. Restart vLLM processes periodically
  4. Implement request pooling to avoid process creation
```

---

## Summary Table: Quick Lookup

| Config | Coder Model | General Model | Total VRAM | Headroom | Fit? |
|--------|------------|---------------|-----------|----------|------|
| Recommended | DeepSeek 33B AWQ | Mistral 7B AWQ | 70 GB | 26 GB | ✓✓✓ |
| Large General | DeepSeek 33B AWQ | Qwen2.5 14B | 80 GB | 16 GB | ✓✓ |
| Qwen Family | Qwen2.5-C 32B AWQ | Qwen2.5 7B | 68 GB | 28 GB | ✓✓✓ |
| Budget FP16 | DeepSeek 33B FP16 | Mistral 7B FP16 | 100 GB | -4 GB | ✗ OOM |
| 8-bit Both | DeepSeek 33B 8-bit | Mistral 7B 8-bit | 88 GB | 8 GB | ✓ (Risky) |
| Single Model | DeepSeek 33B AWQ | - | 50 GB | 46 GB | ✓✓✓ |

