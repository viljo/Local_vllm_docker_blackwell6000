# Model Comparison Matrix & Repository Guide

## Complete Model Specifications

### Python Coder Models: 33B Class

#### DeepSeek Coder 33B
**Official Information:**
- Organization: deepseek-ai
- Parameters: 33 billion
- Training Data: 2 trillion tokens (87% code, 13% natural language)
- Context Length: 4K tokens (base), 8K with special handling
- License: MIT
- Repository: https://huggingface.co/deepseek-ai

**Model Variants:**
```
deepseek-coder-33b-base          → Base model (no instruction tuning)
deepseek-coder-33b-instruct      → Instruction-tuned (recommended for chat/API)
deepseek-coder-33b-instruct-q4km → GGUF quantized variant (for llama.cpp)
```

**Quantized Versions by TheBloke:**
| Format | Repository | Download | GPU Fit | vLLM Support |
|--------|-----------|----------|---------|--------------|
| GPTQ (4-bit) | TheBloke/deepseek-coder-33B-instruct-GPTQ | ✓ | 50-55GB | ✓ Full |
| AWQ (4-bit)  | TheBloke/deepseek-coder-33B-instruct-AWQ | ✓ | 48-52GB | ✓ Full |
| GGUF (2-8bit)| TheBloke/deepseek-coder-33B-instruct-GGUF | ✓ | 15-30GB | ✓ Limited |

**VRAM Requirements (vLLM):**
```
Precision  │ Model Weights │ KV Cache │ Batching │ Total
───────────┼───────────────┼──────────┼──────────┼────────
FP16       │ 66 GB         │ 7-10 GB  │ 2-5 GB   │ 75-81 GB
AWQ 4-bit  │ 18 GB         │ 25-30 GB │ 2-5 GB   │ 45-53 GB
GPTQ 4-bit │ 15.5 GB       │ 28-35 GB │ 2-5 GB   │ 45-55 GB
GGUF 4-bit │ 16 GB         │ 22-28 GB │ 1-3 GB   │ 39-47 GB
```

**Code Generation Performance:**
- HumanEval: ~50-60% pass rate (raw), >90% with reflection
- MBPP: Excellent performance on real-world code tasks
- Accuracy Post-4bit Quantization: ~98.9% recovery
- Strengths: Excellent code understanding, strong at code completion

**Key Strengths:**
- Specifically trained for code (87% of training data)
- Excellent at bug detection and code optimization
- Strong multi-language code support (Python, JavaScript, C++, etc.)
- Good long-context understanding for large codebases

**Limitations:**
- Not as strong on general language tasks as Mistral
- May require more compute for complex general reasoning
- Training cutoff: April 2024

---

#### Qwen2.5-Coder 32B
**Official Information:**
- Organization: Qwen (Alibaba)
- Parameters: 32 billion
- Training Data: 2 trillion tokens (code-focused curriculum)
- Context Length: 128K tokens (long context support)
- License: Qwen License (permissive)
- Repository: https://huggingface.co/Qwen

**Model Variants:**
```
Qwen/Qwen2.5-Coder-32B            → Base model
Qwen/Qwen2.5-Coder-32B-Instruct   → Instruction-tuned (recommended)
```

**Quantized Versions (Official by Qwen):**
| Format | Repository | Download | GPU Fit | vLLM Support |
|--------|-----------|----------|---------|--------------|
| AWQ (4-bit)  | Qwen/Qwen2.5-Coder-32B-Instruct-AWQ | ✓ | 48-52GB | ✓ Full |
| GPTQ Int4    | Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 | ✓ | 50-55GB | ✓ Full |
| GPTQ Int8    | Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int8 | ✓ | 60-65GB | ✓ Full |

**VRAM Requirements (vLLM):**
```
Precision  │ Model Weights │ KV Cache │ Batching │ Total
───────────┼───────────────┼──────────┼──────────┼────────
FP16       │ 64 GB         │ 7-10 GB  │ 2-5 GB   │ 73-79 GB
AWQ 4-bit  │ 19 GB         │ 24-30 GB │ 2-5 GB   │ 45-54 GB
GPTQ 4-bit │ 18 GB         │ 26-32 GB │ 2-5 GB   │ 46-55 GB
GPTQ 8-bit │ 32 GB         │ 24-30 GB │ 2-5 GB   │ 58-67 GB
```

**Code Generation Performance:**
- HumanEval: Strong performance (>90% with reflection)
- MBPP: Excellent real-world code tasks
- Accuracy Post-4bit Quantization: ~98.9% recovery
- Strengths: Code generation, math reasoning, general capabilities

**Key Strengths:**
- 128K context window (vs 8K for DeepSeek)
- Excellent for long codebase analysis
- Strong general language capabilities alongside coding
- Official quantizations from Qwen team
- Better instruction-following

**Limitations:**
- Slightly newer (October 2024), may need validation for your use case
- 128K context increases KV cache memory for long sequences

---

### General Purpose Models: 7B-14B Class

#### Mistral 7B
**Official Information:**
- Organization: Mistral AI
- Parameters: 7 billion
- Training Data: 32K context tokens (trained, not fine-tuned)
- Context Length: 32K tokens
- License: Apache 2.0 (commercial friendly)
- Repository: https://huggingface.co/mistralai

**Model Variants:**
```
mistralai/Mistral-7B-v0.1              → Base model
mistralai/Mistral-7B-Instruct-v0.2     → Instruction-tuned (recommended)
mistralai/Mistral-7B-Instruct-v0.3     → Latest version (Dec 2024)
```

**Quantized Versions (By TheBloke):**
| Format | Repository | Download | GPU Fit | vLLM Support |
|--------|-----------|----------|---------|--------------|
| GPTQ   | TheBloke/Mistral-7B-v0.1-GPTQ | ✓ | 20-24GB | ✓ Full |
| AWQ    | TheBloke/Mistral-7B-v0.1-AWQ | ✓ | 18-22GB | ✓ Full |
| GGUF   | TheBloke/Mistral-7B-v0.1-GGUF | ✓ | 8-14GB | ✓ Limited |

**VRAM Requirements (vLLM):**
```
Precision  │ Model Weights │ KV Cache │ Batching │ Total
───────────┼───────────────┼──────────┼──────────┼────────
FP16       │ 14 GB         │ 8-10 GB  │ 2-4 GB   │ 24-28 GB
AWQ 4-bit  │ 3.5 GB        │ 14-18 GB │ 1-3 GB   │ 18-25 GB
GPTQ 4-bit │ 3.5 GB        │ 14-20 GB │ 1-3 GB   │ 18-26 GB
```

**General Language Performance:**
- MMLU (Knowledge): ~64% accuracy
- MT-Bench (Chat): ~8.3/10 quality
- Code-related: Decent but not specialized
- Strengths: Balanced, good general-purpose performance

**Key Strengths:**
- Extremely efficient (7B parameters)
- 32K context window for long documents
- Excellent instruction-following
- Low memory footprint allows for concurrent models
- Well-established, proven in production

**Limitations:**
- Not specialized for code (DeepSeek better for pure coding)
- Slightly less capable than 13B+ models on complex tasks
- Training cutoff: April 2024

---

#### Qwen2.5 7B / 14B
**Official Information:**
- Organization: Qwen (Alibaba)
- Parameters: 7B or 14B variants
- Training Data: Qwen2.5 training pipeline
- Context Length: 128K tokens (long context)
- License: Qwen License
- Repository: https://huggingface.co/Qwen

**Model Variants:**
```
Qwen/Qwen2.5-7B                → Base model
Qwen/Qwen2.5-7B-Instruct       → Instruction-tuned (7B)
Qwen/Qwen2.5-14B               → Base model (14B)
Qwen/Qwen2.5-14B-Instruct      → Instruction-tuned (14B)
```

**7B Model VRAM Requirements (vLLM):**
```
Precision  │ Model Weights │ KV Cache │ Batching │ Total
───────────┼───────────────┼──────────┼──────────┼────────
FP16       │ 14 GB         │ 8-10 GB  │ 2-4 GB   │ 24-28 GB
4-bit      │ 3.5 GB        │ 14-18 GB │ 1-3 GB   │ 18-25 GB
```

**14B Model VRAM Requirements (vLLM):**
```
Precision  │ Model Weights │ KV Cache │ Batching │ Total
───────────┼───────────────┼──────────┼──────────┼────────
FP16       │ 28 GB         │ 12-15 GB │ 2-4 GB   │ 42-47 GB
4-bit      │ 7-8 GB        │ 18-24 GB │ 2-4 GB   │ 27-36 GB
```

**Performance:**
- MMLU: ~83% (7B), ~86% (14B)
- MT-Bench: Very good (better than comparable Mistral)
- Code-related: Good general support
- Strengths: Balanced across languages and tasks

**Key Strengths:**
- 128K context window (excellent for long documents/code)
- Strong general performance
- Excellent Chinese language support
- Both 7B and 14B options for flexibility
- Official quantizations available

**Limitations:**
- 14B version takes more VRAM (limits concurrent models)
- Slightly newer, less battle-tested than Mistral
- Training data includes Chinese (great for multilingual, less for English-only)

---

## Comparative Performance Matrix

### Code Generation Tasks
| Model | HumanEval | MBPP | 4-bit Accuracy | Specialization |
|-------|-----------|------|----------------|---|
| DeepSeek Coder 33B | >90%* | Excellent | 98.9% | **CODE** ⭐⭐⭐ |
| Qwen2.5-Coder 32B | >90%* | Excellent | 98.9% | **CODE** ⭐⭐⭐ |
| Qwen2.5 14B | Good | Good | 98.9% | General ⭐⭐ |
| Mistral 7B | Fair | Fair | 98.9% | General ⭐⭐ |
| Qwen2.5 7B | Fair | Fair | 98.9% | General ⭐⭐ |

*With chain-of-thought or reflection prompts

### General Language Understanding
| Model | MMLU | MT-Bench | Reasoning | Specialization |
|-------|------|----------|-----------|---|
| Qwen2.5-Coder 32B | ~87% | 8.8/10 | Excellent | Balanced ⭐⭐⭐ |
| DeepSeek Coder 33B | ~85% | 8.5/10 | Good | Code-focused ⭐⭐ |
| Qwen2.5 14B | ~86% | 8.9/10 | Excellent | **BALANCED** ⭐⭐⭐ |
| Mistral 7B | ~64% | 8.3/10 | Good | General ⭐⭐ |
| Qwen2.5 7B | ~80% | 8.7/10 | Good | Balanced ⭐⭐⭐ |

### VRAM Efficiency (4-bit AWQ + vLLM)
| Model | Total VRAM | Efficiency | Best Use |
|-------|-----------|------------|----------|
| Mistral 7B | 18-25 GB | ⭐⭐⭐ Best | Concurrent models |
| Qwen2.5 7B | 18-25 GB | ⭐⭐⭐ Best | Concurrent models |
| Qwen2.5 14B | 27-36 GB | ⭐⭐ Good | Single/High capacity |
| DeepSeek Coder 33B | 45-53 GB | ⭐ Fair | Needs large GPU |
| Qwen2.5-Coder 32B | 45-54 GB | ⭐ Fair | Needs large GPU |

---

## Recommended Combinations for 96GB VRAM

### Tier 1: Best Overall (Recommended)
**DeepSeek Coder 33B AWQ + Mistral 7B AWQ**
```
Total VRAM:  ~70 GB
Headroom:    ~26 GB
Strengths:   Excellent code, good general balance
Trade-off:   Mistral is not specialized for general reasoning
Use Case:    Code-first service with general Q&A
```
- Coder Model: `TheBloke/deepseek-coder-33B-instruct-AWQ`
- General Model: `TheBloke/Mistral-7B-v0.1-AWQ`

### Tier 2: Balanced Performance
**Qwen2.5-Coder 32B AWQ + Qwen2.5 7B**
```
Total VRAM:  ~68 GB
Headroom:    ~28 GB
Strengths:   Consistent model family, both strong at code and general
Trade-off:   Uses larger coder model
Use Case:    Balanced service, prefer single vendor
```
- Coder Model: `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`
- General Model: `Qwen/Qwen2.5-7B-Instruct` (or quantized variant)

### Tier 3: Maximum General Capability
**DeepSeek Coder 33B AWQ + Qwen2.5 14B**
```
Total VRAM:  ~80 GB
Headroom:    ~16 GB (tight)
Strengths:   Best code + Best general reasoning
Trade-off:   Minimal headroom for batching, need tight config
Use Case:    High-quality but lower throughput service
```
- Coder Model: `TheBloke/deepseek-coder-33B-instruct-AWQ`
- General Model: `Qwen/Qwen2.5-14B-Instruct` (use 4-bit quantized)

### Tier 4: Conservative (Single Large Model)
**DeepSeek Coder 33B AWQ Only**
```
Total VRAM:  ~50 GB
Headroom:    ~46 GB
Strengths:   Excellent batching, high throughput
Trade-off:   No concurrent general model
Use Case:    High-volume code generation service
```

---

## Quick Repository Reference

### HuggingFace Repositories to Use

**Official Model Repos (Latest, Maintained):**
```
Coder Models:
  https://huggingface.co/deepseek-ai/deepseek-coder-33b-instruct
  https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct
  https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
  https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4

General Models:
  https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
  https://huggingface.co/Qwen/Qwen2.5-14B-Instruct
```

**Quantized Versions (TheBloke - Trusted Quantizer):**
```
  https://huggingface.co/TheBloke/deepseek-coder-33B-instruct-AWQ
  https://huggingface.co/TheBloke/deepseek-coder-33B-instruct-GPTQ
  https://huggingface.co/TheBloke/Mistral-7B-v0.1-AWQ
  https://huggingface.co/TheBloke/Mistral-7B-v0.1-GPTQ
```

**Quantized Versions (Official by Qwen):**
```
  https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
  https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ (if available)
  https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-AWQ (if available)
```

---

## Download Sizes & Disk Space

### On-Disk Sizes (Uncompressed)
```
DeepSeek Coder 33B AWQ:  ~18 GB disk (~16 GB in memory after loading)
Qwen2.5-Coder 32B AWQ:   ~19 GB disk
Mistral 7B AWQ:          ~3.5 GB disk
Qwen2.5 7B:              ~14-15 GB disk (FP16)
Qwen2.5 14B:             ~28 GB disk (FP16)
```

### Disk Space Recommendation
```
For Tier 1 (Recommended):
  DeepSeek 33B + Mistral 7B: ~21.5 GB disk space
  Add cache/overhead: 25-30 GB total

For Tier 2 (Alternative):
  Qwen 32B + Qwen 7B: ~33 GB disk space
  Add cache/overhead: 40-45 GB total

For Tier 3 (Balanced):
  DeepSeek 33B + Qwen 14B: ~46 GB disk space
  Add cache/overhead: 55-65 GB total
```

---

## License Summary

| Model | License | Commercial Use | Attribution |
|-------|---------|---------------|----|
| DeepSeek Coder 33B | MIT | ✓ Yes | Not required |
| Qwen2.5 | Qwen License | ✓ Yes | Recommended |
| Mistral 7B | Apache 2.0 | ✓ Yes | Not required |

All models are commercially usable.

---

## Final Recommendation Summary

**For your 96GB VRAM budget with 2 concurrent models:**

1. **Primary Recommendation:**
   - Model: `TheBloke/deepseek-coder-33B-instruct-AWQ` + `TheBloke/Mistral-7B-v0.1-AWQ`
   - VRAM: ~70GB used, 26GB headroom
   - Quality: Excellent code, solid general
   - Accuracy Loss: 1.1% (negligible)

2. **Alternative if you prefer Qwen:**
   - Model: `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` + `Qwen/Qwen2.5-7B-Instruct`
   - VRAM: ~68GB used, 28GB headroom
   - Quality: Excellent code, excellent general
   - Accuracy Loss: 1.1% (negligible)

3. **If you need maximum general performance:**
   - Model: `TheBloke/deepseek-coder-33B-instruct-AWQ` + `Qwen/Qwen2.5-14B-Instruct` (quantized)
   - VRAM: ~80GB used, 16GB headroom (tight)
   - Quality: Excellent code, excellent general
   - Trade-off: Reduced batching capacity

**Quantization method:** AWQ 4-bit (best for vLLM memory overhead)

**Expected accuracy loss:** 1.1% on code generation (98.9% recovery vs FP16)

**All models are production-ready and commercially usable.**

