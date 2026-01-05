# Self-Hosted LLM Guide: From Zero to Production

## Table of Contents
1. [Why Self-Host?](#1-why-self-host)
2. [Model Selection](#2-model-selection)
3. [vLLM Deep Dive](#3-vllm-deep-dive)
4. [Hardware Requirements](#4-hardware-requirements)
5. [Implementation](#5-implementation)
6. [Fine-Tuning](#6-fine-tuning)
7. [Scaling Strategies](#7-scaling-strategies)
8. [Monitoring & Optimization](#8-monitoring--optimization)

---

## 1. Why Self-Host?

### Cost Comparison

Let's do real math for your Character Chat app:

```
SCENARIO: 10,000 users, 50 messages/day average

OpenAI GPT-4o-mini:
├── Input: ~500 tokens/request × 500,000 requests/day = 250M tokens
├── Output: ~200 tokens/request × 500,000 requests/day = 100M tokens
├── Cost: (250M × $0.15/1M) + (100M × $0.60/1M) = $37.50 + $60 = $97.50/day
└── Monthly: ~$3,000/month

Self-Hosted (Llama 3.1 8B on A100):
├── A100 80GB rental: ~$2/hour = $1,440/month
├── Can handle: ~50-100 requests/second = WAY more than needed
├── Monthly: ~$1,500/month (with redundancy)
└── SAVINGS: 50% + you OWN the infrastructure

At 100,000 users:
├── OpenAI: ~$30,000/month
├── Self-hosted: ~$3,000/month (add more GPUs)
└── SAVINGS: 90%
```

### Beyond Cost: Other Benefits

| Benefit | Why It Matters |
|---------|----------------|
| **Latency** | Self-hosted = 50-200ms, OpenAI = 500-2000ms |
| **Privacy** | User data never leaves your servers |
| **Customization** | Fine-tune for YOUR use case |
| **No Rate Limits** | Scale to your hardware, not API limits |
| **Reliability** | No dependency on external service |
| **Predictable Costs** | Fixed GPU cost vs variable API cost |

### When NOT to Self-Host

- Prototype/MVP stage (use OpenAI, validate idea first)
- <1000 users (not worth the operational overhead)
- Need GPT-4 level reasoning (open-source catching up but not there yet)
- No ML engineering capacity

---

## 2. Model Selection

### For Character Chat, You Need:

1. **Strong instruction following** (stay in character)
2. **Good creative writing** (engaging dialogue)
3. **Long context** (conversation history + memories)
4. **Fast inference** (real-time chat)

### Recommended Models (2024)

| Model | Size | Context | Best For | VRAM Needed |
|-------|------|---------|----------|-------------|
| **Llama 3.1 8B Instruct** | 8B | 128K | Best balance of speed/quality | 16GB |
| **Llama 3.1 70B Instruct** | 70B | 128K | Highest quality open-source | 140GB (2×A100) |
| **Mistral 7B Instruct** | 7B | 32K | Fast, good quality | 14GB |
| **Mixtral 8x7B** | 47B | 32K | MoE, great quality/speed | 90GB |
| **Qwen2.5 7B/72B** | 7-72B | 128K | Strong multilingual | 14-150GB |
| **Yi-1.5 34B** | 34B | 200K | Very long context | 68GB |

### My Recommendation for Character Chat

**Start with: Llama 3.1 8B Instruct**

Why:
- 128K context (fits all your memories + history)
- Fast inference (~50 tokens/sec on A100)
- Great instruction following
- Can fine-tune on character dialogues later
- Runs on single consumer GPU (RTX 4090) for dev

**Scale to: Llama 3.1 70B or fine-tuned 8B**

---

## 3. vLLM Deep Dive

### What is vLLM?

vLLM is a high-throughput LLM serving library. It's what companies like Anyscale use in production.

### Key Innovation: PagedAttention

Traditional LLM serving wastes GPU memory because attention KV cache is allocated contiguously:

```
Traditional:
┌─────────────────────────────────────────────┐
│ Request 1 KV Cache [████████░░░░░░░░░░░░░]  │ ← Allocated for max_length
│ Request 2 KV Cache [██████░░░░░░░░░░░░░░░]  │ ← Even if response is short
│ Request 3 KV Cache [████░░░░░░░░░░░░░░░░░]  │ ← Huge waste!
└─────────────────────────────────────────────┘

PagedAttention (vLLM):
┌─────────────────────────────────────────────┐
│ Page Pool: [1][2][3][4][5][6][7][8][9]...   │
│ Request 1: Pages [1,3,5,7]                   │ ← Only allocate what's used
│ Request 2: Pages [2,4,6]                     │ ← Pages can be non-contiguous
│ Request 3: Pages [8,9]                       │ ← Memory efficient!
└─────────────────────────────────────────────┘
```

**Result:** 2-4x higher throughput, 24x more concurrent requests

### vLLM Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         vLLM Server                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   FastAPI    │    │   Scheduler  │    │   Model Runner   │   │
│  │   Endpoint   │───▶│              │───▶│                  │   │
│  │              │    │ • Batching   │    │ • GPU Execution  │   │
│  │ /v1/chat     │    │ • Priority   │    │ • KV Cache Mgmt  │   │
│  │ /v1/complete │    │ • Preemption │    │ • PagedAttention │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│                                                   │              │
│                                                   ▼              │
│                              ┌────────────────────────────────┐  │
│                              │         GPU Memory             │  │
│                              │  ┌─────────┐ ┌──────────────┐  │  │
│                              │  │ Model   │ │  KV Cache    │  │  │
│                              │  │ Weights │ │  Page Pool   │  │  │
│                              │  │ (Fixed) │ │  (Dynamic)   │  │  │
│                              │  └─────────┘ └──────────────┘  │  │
│                              └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Key vLLM Concepts

#### 1. Continuous Batching
Traditional: Wait for batch to complete, then process next batch
vLLM: As soon as one request finishes, immediately add new request to batch

```python
# Traditional (inefficient)
batch = [req1, req2, req3]
results = model.generate(batch)  # Must wait for slowest
# Then start next batch...

# vLLM Continuous Batching
# req1 finishes → immediately add req4 to running batch
# No waiting! GPU always busy
```

#### 2. Speculative Decoding
Use small "draft" model to predict multiple tokens, verify with main model:

```
Draft model (fast):     "The" → "quick" → "brown" → "fox"
Main model (accurate):  Verify all 4 at once ✓ ✓ ✓ ✓
Result: 4 tokens in ~1 forward pass instead of 4
```

#### 3. Tensor Parallelism
Split model across multiple GPUs:

```
Single GPU:          Multi-GPU (Tensor Parallel):
┌─────────────┐      ┌──────────┐ ┌──────────┐
│   Layer 1   │      │ Layer 1  │ │ Layer 1  │
│   Layer 2   │  →   │   (half) │ │  (half)  │
│   Layer 3   │      │ Layer 2  │ │ Layer 2  │
│   Layer 4   │      │   (half) │ │  (half)  │
│  (all on    │      │  GPU 0   │ │  GPU 1   │
│   one GPU)  │      └──────────┘ └──────────┘
└─────────────┘      Results combined via NVLink
```

### vLLM vs Alternatives

| Feature | vLLM | TGI (HuggingFace) | Ollama | llama.cpp |
|---------|------|-------------------|--------|-----------|
| **Throughput** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Latency** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Ease of Use** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Production Ready** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Multi-GPU** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ⭐⭐ |
| **OpenAI Compatible** | ✅ | ✅ | ✅ | ❌ |

**Verdict:** Use vLLM for production, Ollama for local dev

---

## 4. Hardware Requirements

### GPU Memory Calculation

```python
# Formula for model memory (FP16)
model_memory_gb = (num_parameters * 2) / (1024**3)

# Examples:
# Llama 3.1 8B:  8B × 2 bytes = 16 GB
# Llama 3.1 70B: 70B × 2 bytes = 140 GB
# Mixtral 8x7B:  47B × 2 bytes = 94 GB

# KV Cache per token (FP16)
kv_cache_per_token = 2 * num_layers * hidden_size * 2  # bytes

# Llama 3.1 8B: 2 * 32 * 4096 * 2 = 524KB per token
# With 128K context: 524KB × 128K = 67 GB (!)
# This is why PagedAttention matters
```

### Recommended Setups

#### Development (Local)
```
Option A: RTX 4090 (24GB)
├── Models: Llama 8B, Mistral 7B, Qwen 7B
├── Context: ~8K tokens
├── Cost: $1,600 one-time
└── Good for: Dev, testing, fine-tuning small models

Option B: 2× RTX 3090 (48GB total)
├── Models: Llama 8B with longer context, or 13B models
├── Cost: $1,400 one-time
└── Good for: Dev with more headroom
```

#### Production (Cloud)
```
Small Scale (10K users):
├── 1× A100 80GB or 2× A10 24GB
├── Provider: Lambda Labs, RunPod, Vast.ai
├── Cost: $1-2/hour
└── Models: Llama 8B, Mistral 7B

Medium Scale (100K users):
├── 2-4× A100 80GB
├── Provider: AWS, GCP, CoreWeave
├── Cost: $4-8/hour
└── Models: Llama 70B, Mixtral

Large Scale (1M+ users):
├── 8+ A100/H100 cluster
├── Provider: CoreWeave, Lambda
├── Cost: $20+/hour
└── Models: Multiple replicas, load balanced
```

### Cost Comparison: Cloud GPUs

| Provider | GPU | VRAM | $/hour | Best For |
|----------|-----|------|--------|----------|
| **RunPod** | A100 80GB | 80GB | $1.89 | Dev/Testing |
| **Vast.ai** | A100 80GB | 80GB | $1.50-2.50 | Cheapest |
| **Lambda** | A100 80GB | 80GB | $2.49 | Reliable |
| **AWS** | A100 | 40GB | $4.10 | Enterprise |
| **GCP** | A100 | 40GB | $3.67 | Enterprise |
| **CoreWeave** | A100 | 80GB | $2.21 | Production |

---

## 5. Implementation

See the code implementation in the next files:
- `app/llm/providers/base.py` - Abstract LLM interface
- `app/llm/providers/vllm_provider.py` - vLLM implementation
- `app/llm/providers/ollama_provider.py` - Local dev with Ollama
- `docker/vllm/docker-compose.yml` - vLLM deployment

---

## 6. Fine-Tuning

### Why Fine-Tune for Character Chat?

Base models are trained on general text. Fine-tuning teaches:
- How to stay in character consistently
- Speaking patterns of specific character types
- Appropriate response length
- When to be dramatic vs casual

### Fine-Tuning Methods

| Method | Description | When to Use |
|--------|-------------|-------------|
| **Full Fine-Tune** | Update all weights | Maximum quality, expensive |
| **LoRA** | Low-rank adaptation | Best balance of quality/cost |
| **QLoRA** | Quantized LoRA | Even cheaper, slight quality loss |
| **Prompt Tuning** | Learn soft prompts | Cheapest, limited improvement |

### LoRA Explained

Instead of updating all 8B parameters, LoRA adds small trainable matrices:

```
Original weight W (8B params, frozen):
┌─────────────────────────────────────┐
│  W (d × k) - NOT UPDATED           │
└─────────────────────────────────────┘

LoRA adds:
┌─────────┐   ┌─────────┐
│ A (d×r) │ × │ B (r×k) │  where r << d, k (e.g., r=8)
└─────────┘   └─────────┘
     │             │
     └──────┬──────┘
            ▼
    Only train A and B!
    8B → ~1M trainable params
```

### Dataset for Character Chat Fine-Tuning

```json
// character_chat_dataset.jsonl
{"messages": [
  {"role": "system", "content": "You are Batman, the Dark Knight..."},
  {"role": "user", "content": "Why do you fight crime?"},
  {"role": "assistant", "content": "Because someone has to. Gotham needs a symbol..."}
]}
{"messages": [
  {"role": "system", "content": "You are Sherlock Holmes..."},
  {"role": "user", "content": "How did you know I was a doctor?"},
  {"role": "assistant", "content": "Elementary. The calluses on your hands..."}
]}
```

Need ~1000-10000 examples for good results.

---

## 7. Scaling Strategies

### Horizontal Scaling

```
Load Balancer (nginx/HAProxy)
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ vLLM 1 │ │ vLLM 2 │  ← Same model, multiple instances
│ (GPU 0)│ │ (GPU 1)│
└────────┘ └────────┘
```

### Request Routing Strategies

1. **Round Robin** - Simple, equal distribution
2. **Least Connections** - Route to least busy server
3. **Consistent Hashing** - Same user → same server (cache benefits)

### Auto-Scaling

```yaml
# Kubernetes HPA example
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: nvidia.com/gpu
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 8. Monitoring & Optimization

### Key Metrics to Track

| Metric | Target | Why |
|--------|--------|-----|
| **Tokens/second** | 50+ | Throughput |
| **Time to First Token (TTFT)** | <500ms | User experience |
| **Request Latency (P99)** | <3s | Tail latency |
| **GPU Utilization** | 70-90% | Efficiency |
| **Queue Depth** | <100 | Backpressure |
| **Error Rate** | <0.1% | Reliability |

### Optimization Techniques

1. **Quantization** (INT8/INT4) - 2-4x faster, slight quality loss
2. **Flash Attention** - Faster attention computation
3. **Speculative Decoding** - Use draft model for speed
4. **Prompt Caching** - Cache common prefixes
5. **Batching Tuning** - Optimize batch size for your load

---

## Quick Start Commands

```bash
# Local dev with Ollama
ollama pull llama3.1:8b
ollama serve

# Production with vLLM
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 8192

# Fine-tuning with LoRA
python -m axolotl train config.yaml
```

See implementation files for full code.

