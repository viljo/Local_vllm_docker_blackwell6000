# Quantization Research: 96GB VRAM Budget for Concurrent Model Inference

## Executive Summary

With a 96GB VRAM budget for running 2 models concurrently, **quantization is essential**. FP16 alone would require 65-130GB VRAM. Using 4-bit quantization (AWQ preferred) for both models keeps total usage well under 96GB with minimal accuracy loss for code generation tasks.

---

## 1. VRAM Requirements by Model and Precision

### Model 1: Python Coder (33B Models)

#### DeepSeek Coder 33B
| Precision | Model Weights Only | vLLM with KV Cache |
|-----------|-------------------|------------------|
| FP16      | 66 GB             | ~70-75 GB        |
| GPTQ 4-bit| 15.54 GB          | ~50-55 GB        |
| AWQ 4-bit | 18.01 GB          | ~48-52 GB        |

**DeepSeek Coder 33B Sources:**
- Official: `deepseek-ai/deepseek-coder-33b-instruct`
- Quantized (GPTQ): `TheBloke/deepseek-coder-33B-instruct-GPTQ`
- Quantized (AWQ): `TheBloke/deepseek-coder-33B-instruct-AWQ`

#### Qwen2.5-Coder 32B (Similar to 33B)
| Precision | Model Weights Only | vLLM with KV Cache |
|-----------|-------------------|------------------|
| FP16      | 64-65 GB          | ~68-73 GB        |
| GPTQ 4-bit| 23.7 GB           | ~50-55 GB        |
| AWQ 4-bit | ~20 GB            | ~48-52 GB        |

**Qwen2.5-Coder 32B Sources:**
- Official: `Qwen/Qwen2.5-Coder-32B-Instruct`
- Quantized (AWQ): `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`
- Quantized (GPTQ-Int4): `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4`
- Quantized (GPTQ-Int8): `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int8`

---

### Model 2: General Purpose (7B-14B Models)

#### Mistral 7B
| Precision | Model Weights Only | vLLM with KV Cache |
|-----------|-------------------|------------------|
| FP16      | 13.74 GB          | ~24-28 GB        |
| GPTQ 4-bit| 3.5-6 GB          | ~20-24 GB        |
| AWQ 4-bit | 3.5 GB            | ~18-22 GB        |

**Mistral 7B Sources:**
- Official: `mistralai/Mistral-7B-Instruct-v0.2`
- Quantized (AWQ): `TheBloke/Mistral-7B-v0.1-AWQ`

#### Qwen2.5 7B
| Precision | Model Weights Only | vLLM with KV Cache |
|-----------|-------------------|------------------|
| FP16      | ~14 GB            | ~17-24 GB        |
| 4-bit     | ~3.5-5 GB         | ~15-20 GB        |

#### Qwen2.5 14B
| Precision | Model Weights Only | vLLM with KV Cache |
|-----------|-------------------|------------------|
| FP16      | ~28 GB            | ~35-42 GB        |
| 4-bit     | ~7-8 GB           | ~25-32 GB        |

**Qwen2.5 7B/14B Sources:**
- Official: `Qwen/Qwen2.5-7B-Instruct`, `Qwen/Qwen2.5-14B-Instruct`
- Quantized versions available on Qwen HuggingFace org

---

## 2. VRAM Budget Analysis: Concurrent Models

### Scenario A: Recommended (4-bit Quantization)
**DeepSeek Coder 33B (4-bit AWQ) + Mistral 7B (4-bit AWQ)**
```
DeepSeek Coder 33B AWQ:  ~50 GB
Mistral 7B AWQ:         ~20 GB
---
Total:                   ~70 GB (within 96GB budget)
Headroom:                ~26 GB (for batching, inference overhead)
```

### Scenario B: Alternative (Qwen Models)
**Qwen2.5-Coder 32B (4-bit AWQ) + Qwen2.5 7B (4-bit)**
```
Qwen2.5-Coder 32B AWQ:  ~50 GB
Qwen2.5 7B:             ~18 GB
---
Total:                   ~68 GB (within 96GB budget)
Headroom:                ~28 GB
```

### Scenario C: Larger General Model
**DeepSeek Coder 33B (4-bit AWQ) + Qwen2.5 14B (4-bit)**
```
DeepSeek Coder 33B AWQ:  ~50 GB
Qwen2.5 14B:             ~30 GB
---
Total:                   ~80 GB (within 96GB budget)
Headroom:                ~16 GB (tight, but workable)
```

### What DOESN'T Fit: FP16
**DeepSeek Coder 33B (FP16) + Mistral 7B (FP16)**
```
DeepSeek Coder 33B FP16: ~70 GB
Mistral 7B FP16:         ~24 GB
---
Total:                   ~94 GB (exceeds headroom needed)
❌ Not recommended - no room for inference overhead
```

---

## 3. Quantization Method Comparison: GPTQ vs AWQ

### vLLM Support
| Method | Support | Notes |
|--------|---------|-------|
| GPTQ   | Full    | `--quantization gptq` flag, broad GPU support |
| AWQ    | Full    | `--quantization awq` flag, preferred for vLLM |

### Memory Usage (vLLM)
- **AWQ**: ~48.44 GB for Mistral 7B (better)
- **GPTQ**: ~66.44 GB for Mistral 7B (higher)
- **Winner**: AWQ uses significantly less memory in vLLM

### Accuracy on Code Generation Tasks
| Metric | GPTQ | AWQ | Notes |
|--------|------|-----|-------|
| 4-bit Accuracy Recovery | 98.9% | 98.9%+ | Near-identical for most tasks |
| HumanEval Performance | Strong | Strong | Both maintain >98% accuracy |
| MBPP Benchmark | Excellent | Excellent | Code generation performs well |
| General Language Tasks | Good | Better | AWQ slightly better on MT-Bench |
| Instruction Following | GPTQ Better | Good | GPTQ has edge on some instruction models |

### Key Differences
- **AWQ (Activation-Aware Weight Quantization)**
  - Protects only 1% of weights from quantization
  - Better for general tasks and language understanding
  - Lower memory overhead in vLLM (~4-6 GB less)
  - Faster quantization process

- **GPTQ (GPT Quantization)**
  - Layer-wise quantization with Hessian-based optimization
  - Better for instruction-tuned models
  - Slightly higher memory footprint in vLLM
  - More established/mature

### Recommendation for Your Use Case
**Use AWQ** for both models because:
1. Lower vLLM memory overhead (critical for 96GB budget)
2. Equivalent code generation accuracy (98.9% recovery)
3. Better on general language tasks (Mistral 7B)
4. Adequate for instruction-tuned models (small performance trade-off acceptable)

---

## 4. Pre-Quantized Model Repositories

### DeepSeek Coder 33B
| Format | Repository | Link |
|--------|-----------|------|
| Official Base | deepseek-ai | `deepseek-ai/deepseek-coder-33b-base` |
| Official Instruct | deepseek-ai | `deepseek-ai/deepseek-coder-33b-instruct` |
| GPTQ 4-bit | TheBloke | `TheBloke/deepseek-coder-33B-instruct-GPTQ` |
| AWQ 4-bit | TheBloke | `TheBloke/deepseek-coder-33B-instruct-AWQ` |
| GGUF | TheBloke | `TheBloke/deepseek-coder-33B-instruct-GGUF` |

### Qwen2.5-Coder 32B
| Format | Repository | Link |
|--------|-----------|------|
| Official Base | Qwen | `Qwen/Qwen2.5-Coder-32B` |
| Official Instruct | Qwen | `Qwen/Qwen2.5-Coder-32B-Instruct` |
| AWQ 4-bit | Qwen | `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` |
| GPTQ 4-bit | Qwen | `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4` |
| GPTQ 8-bit | Qwen | `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int8` |

### Mistral 7B
| Format | Repository | Link |
|--------|-----------|------|
| Official Instruct | mistralai | `mistralai/Mistral-7B-Instruct-v0.2` |
| AWQ 4-bit | TheBloke | `TheBloke/Mistral-7B-v0.1-AWQ` |
| GPTQ 4-bit | TheBloke | `TheBloke/Mistral-7B-v0.1-GPTQ` |

### Qwen2.5 7B / 14B
| Format | Repository | Link |
|--------|-----------|------|
| Official 7B | Qwen | `Qwen/Qwen2.5-7B-Instruct` |
| Official 14B | Qwen | `Qwen/Qwen2.5-14B-Instruct` |
| Quantized | Qwen | Check Qwen HuggingFace org for AWQ/GPTQ variants |

---

## 5. Accuracy Impact: 4-bit Quantization on Code Generation

### Measured Accuracy Recovery
- **8-bit quantization**: 99.9% accuracy recovery
- **4-bit quantization**: 98.9% accuracy recovery
- **Baseline**: Full-precision (FP16/BF16) model

### Code Generation Benchmarks
- **HumanEval**: Both GPTQ and AWQ maintain excellent performance
- **MBPP**: Code generation tasks show minimal degradation
- **HumanEval Plus**: 4-bit models recover 98.9% of baseline accuracy

### Practical Impact
For code generation tasks, the 1.1% accuracy loss is negligible:
- Typical code generation success rates remain >98%
- Edge cases and complex algorithms may have slightly higher failure rates
- For most production use cases, the performance is acceptable

### Real-World Assessment
According to comprehensive evaluations over 500,000+ test runs:
- No significant difference in output quality for common programming tasks
- Edge cases are rare enough that typical workloads are unaffected
- Code syntax errors slightly increased but still <1% additional failure rate

---

## 6. vLLM-Specific Optimizations & VRAM Usage

### PagedAttention
**Memory Efficiency:**
- Stores KV cache in non-contiguous memory blocks
- Reduces memory waste from <25% to <4% of KV cache size
- Enables up to 96% reduction in KV cache fragmentation

**Impact on Your Setup:**
- Automatically enabled in vLLM
- Allows both models to share GPU memory more efficiently
- Critical for fitting concurrent models

### Continuous Batching
**How it Helps:**
- Dynamically replaces completed sequences with new ones
- Eliminates waiting for entire batch to finish
- Enables 23x throughput improvement over static batching

**For Concurrent Models:**
- Requests can be distributed between models dynamically
- Better GPU utilization = less peak VRAM needed
- vLLM scheduler balances memory load across models

### GPU Memory Utilization Parameter
```bash
# Default: vLLM allocates 90% of available GPU memory
vllm serve <model> --gpu-memory-utilization 0.9

# For concurrent models, consider reducing to 0.85:
vllm serve <model1> --gpu-memory-utilization 0.85
# (Each model gets proportional allocation)
```

### Batching Configuration
```bash
# Control token batching (affects KV cache size)
--max-num-batched-tokens <number>

# Default is usually 8192-20480
# Higher values = larger KV cache = more VRAM needed
# For 96GB with concurrent models: consider 8192-12288
```

### Multi-GPU Strategy (If Available)
If you have 2 GPUs with 48GB each:
```bash
# Option 1: One model per GPU
# GPU 0: DeepSeek Coder 33B AWQ (50GB with headroom)
# GPU 1: Mistral 7B AWQ (20GB with headroom)

# Option 2: Tensor parallelism (split one model)
# For single 96GB GPU with concurrent models, use:
--tensor-parallel-size 1  # No parallelism needed if models fit
```

---

## 7. Recommended Configuration for 96GB VRAM

### Best Option: DeepSeek Coder 33B + Mistral 7B (Both AWQ 4-bit)

**Model Selection:**
```
Coder Model:    deepseek-coder-33b-instruct (use AWQ quantized)
General Model:  mistral-7b-instruct-v0.2 (use AWQ quantized)
Quantization:   AWQ 4-bit
```

**vLLM Launch Configuration:**
```bash
# Model 1: DeepSeek Coder 33B
python -m vllm.entrypoints.api_server \
  --model TheBloke/deepseek-coder-33B-instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.88 \
  --max-num-batched-tokens 8192 \
  --port 8000

# Model 2: Mistral 7B (same GPU or separate if multi-GPU)
python -m vllm.entrypoints.api_server \
  --model TheBloke/Mistral-7B-v0.1-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.88 \
  --max-num-batched-tokens 8192 \
  --port 8001
```

**Expected VRAM Usage:**
```
DeepSeek Coder 33B AWQ:  ~50 GB (model + KV cache buffer)
Mistral 7B AWQ:          ~20 GB (model + KV cache buffer)
System/Headroom:         ~26 GB
---
Total:                   ~96 GB ✓
```

**Tuning if Memory Tight:**
```bash
# Reduce GPU memory utilization to 0.85 (5% reserve):
--gpu-memory-utilization 0.85

# Reduce batched tokens (smaller KV cache per request):
--max-num-batched-tokens 6144

# Use smaller max-num-seqs:
--max-num-seqs 128  # Default is often 256
```

---

## 8. Alternative Configurations to Consider

### Option 2: Qwen Models (Similar Size)
**Qwen2.5-Coder 32B AWQ + Qwen2.5 7B**
- More consistent model family
- Official Qwen quantizations available
- Similar VRAM usage and accuracy

### Option 3: Single Larger Model Alternative
If concurrent inference isn't critical:
- **DeepSeek Coder 33B AWQ**: ~50 GB
- Leaves 46GB for batching and other tasks
- Better for high-throughput single-model serving

### Option 4: Use 8-bit Quantization Instead
- Slightly higher accuracy (99.5% recovery vs 98.9%)
- Higher VRAM: ~60GB for 33B model in vLLM
- Trade-off: smaller headroom for concurrent batching

---

## 9. Summary & Recommendations

### Does Quantization Fit in 96GB?
**YES** - With AWQ 4-bit quantization:
- DeepSeek Coder 33B (50GB) + Mistral 7B (20GB) = 70GB
- Comfortable 26GB headroom for batching and overhead

### Will FP16 Fit?
**NO** - FP16 requires 65GB+ per model
- Not feasible for concurrent inference
- Quantization is necessary

### Best Quantization Method?
**AWQ 4-bit**
- 98.9% accuracy recovery for code generation
- Lower vLLM memory overhead than GPTQ
- Equivalent performance on code benchmarks

### Pre-Quantized Models to Use?
**TheBloke & Official Qwen Repositories**
- `TheBloke/deepseek-coder-33B-instruct-AWQ` (DeepSeek)
- `TheBloke/Mistral-7B-v0.1-AWQ` (Mistral)
- `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (Qwen alternative)

### Expected Quality Loss?
**Minimal (<1.1% accuracy loss)**
- Code generation: 98.9% accuracy recovery
- General language: AWQ near-parity with FP16
- Negligible impact for production use

### Performance Optimizations?
**Enable these automatically in vLLM:**
- PagedAttention: Reduces KV cache waste to <4%
- Continuous Batching: 23x throughput improvement
- Dynamic scheduling: Automatic model load balancing

---

## 10. Final Recommendation

**Configuration: DeepSeek Coder 33B (AWQ) + Mistral 7B (AWQ)**

| Parameter | Value | Reason |
|-----------|-------|--------|
| Coder Model | DeepSeek 33B | Best code performance (trained on 87% code) |
| General Model | Mistral 7B | Efficient, excellent quality |
| Quantization | AWQ 4-bit | Lowest vLLM memory overhead, best accuracy |
| Repositories | TheBloke/Qwen official | Pre-quantized, maintained, vLLM compatible |
| Budget Fit | ~70GB of 96GB | 26GB headroom for inference overhead |
| Accuracy | 98.9% recovery | Negligible loss for code generation |
| Implementation | vLLM | Native quantization support, excellent batching |

This configuration provides the best balance of model quality, quantization efficiency, and budget adherence.
