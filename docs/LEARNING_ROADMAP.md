# 🎓 Self-Hosted LLM Learning Roadmap

## Overview

This document is your guided learning path for mastering self-hosted LLMs. Each section builds on the previous one. Take your time to understand each concept before moving on.

---

## Phase 1: Understanding LLM Economics (Day 1)

### 📖 Read
- `docs/SELF_HOSTED_LLM_GUIDE.md` - Section 1: Why Self-Host?

### 🧮 Exercise: Calculate Your Costs

```python
# Calculate your projected costs
# Adjust these numbers for your use case

users = 10000
messages_per_day = 50
avg_input_tokens = 500  # System prompt + history + user message
avg_output_tokens = 200  # Character response

# OpenAI Pricing (GPT-4o-mini)
input_cost_per_1m = 0.15  # $/1M tokens
output_cost_per_1m = 0.60  # $/1M tokens

daily_input_tokens = users * messages_per_day * avg_input_tokens
daily_output_tokens = users * messages_per_day * avg_output_tokens

daily_cost = (
    (daily_input_tokens / 1_000_000) * input_cost_per_1m +
    (daily_output_tokens / 1_000_000) * output_cost_per_1m
)

monthly_cost = daily_cost * 30

print(f"Daily tokens: {daily_input_tokens + daily_output_tokens:,}")
print(f"Daily cost: ${daily_cost:.2f}")
print(f"Monthly cost: ${monthly_cost:.2f}")

# Now compare with self-hosted:
# A100 80GB: ~$2/hour = $1,440/month
# Can handle 50+ requests/second = way more than needed
```

### ✅ Checkpoint
- [ ] I understand why self-hosting makes sense at scale
- [ ] I can calculate my projected costs
- [ ] I know the break-even point for my use case

---

## Phase 2: Model Selection (Day 1-2)

### 📖 Read
- `docs/SELF_HOSTED_LLM_GUIDE.md` - Section 2: Model Selection
- https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard

### 🔬 Exercise: Test Different Models

```bash
# Install Ollama for easy model testing
# Windows: Download from ollama.com
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh

# Pull and test different models
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull qwen2.5:7b

# Test each one with a character prompt
ollama run llama3.1:8b "You are Sherlock Holmes. The user asks: How do you solve mysteries?"
```

### Compare Models

| Model | Response Quality | Speed | Memory |
|-------|-----------------|-------|--------|
| Llama 3.1 8B | | | |
| Mistral 7B | | | |
| Qwen 2.5 7B | | | |

Rate each 1-5 for your character chat use case.

### ✅ Checkpoint
- [ ] I've tested at least 3 models
- [ ] I understand the quality/speed/memory trade-offs
- [ ] I've chosen a primary model for my use case

---

## Phase 3: vLLM Deep Dive (Day 2-3)

### 📖 Read
- `docs/SELF_HOSTED_LLM_GUIDE.md` - Section 3: vLLM Deep Dive
- `app/llm/providers/vllm_provider.py` - Read the code comments

### 🔧 Exercise: Run vLLM

```bash
# Option 1: Docker (recommended)
.\scripts\start_vllm.ps1 docker  # Windows
./scripts/start_vllm.sh docker   # Linux/Mac

# Option 2: Direct Python
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --max-model-len 8192

# Test the API
curl http://localhost:8000/v1/models
curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [
            {"role": "system", "content": "You are Batman."},
            {"role": "user", "content": "Who are you?"}
        ]
    }'
```

### 🧪 Benchmark Exercise

```python
# benchmark.py - Measure performance
import asyncio
import httpx
import time

async def benchmark_vllm(num_requests: int = 10):
    """Measure throughput and latency."""
    
    async with httpx.AsyncClient() as client:
        start = time.time()
        latencies = []
        
        for i in range(num_requests):
            req_start = time.time()
            
            response = await client.post(
                "http://localhost:8000/v1/chat/completions",
                json={
                    "model": "meta-llama/Llama-3.1-8B-Instruct",
                    "messages": [
                        {"role": "system", "content": "You are Batman, the Dark Knight of Gotham."},
                        {"role": "user", "content": f"Tell me about yourself. (Request {i})"}
                    ],
                    "max_tokens": 200
                },
                timeout=60
            )
            
            latency = time.time() - req_start
            latencies.append(latency)
            print(f"Request {i}: {latency:.2f}s")
        
        total_time = time.time() - start
        
        print(f"\n=== Results ===")
        print(f"Total time: {total_time:.2f}s")
        print(f"Requests/second: {num_requests/total_time:.2f}")
        print(f"Average latency: {sum(latencies)/len(latencies):.2f}s")
        print(f"P95 latency: {sorted(latencies)[int(len(latencies)*0.95)]:.2f}s")

asyncio.run(benchmark_vllm(10))
```

### ✅ Checkpoint
- [ ] I can start vLLM server
- [ ] I understand the API format (OpenAI-compatible)
- [ ] I've benchmarked my setup
- [ ] I know my throughput and latency numbers

---

## Phase 4: Integration (Day 3-4)

### 📖 Read
- `app/llm/config.py` - Configuration system
- `app/llm/factory.py` - Factory pattern
- `app/llm/providers/base.py` - Provider interface

### 🔧 Exercise: Switch Providers

```python
# test_providers.py
import asyncio
import os
from app.llm import get_llm
from app.llm.providers.base import Message, MessageRole

async def test_provider(provider: str):
    """Test a specific provider."""
    os.environ["LLM_PROVIDER"] = provider
    
    # Clear cache to pick up new provider
    from app.llm.factory import clear_cache
    clear_cache()
    
    llm = get_llm()
    print(f"\nTesting {provider} ({llm.model_name})...")
    
    messages = [
        Message(MessageRole.SYSTEM, "You are Sherlock Holmes."),
        Message(MessageRole.USER, "How do you solve cases?")
    ]
    
    result = await llm.chat(messages)
    print(f"Response: {result.text[:200]}...")
    print(f"Tokens: {result.total_tokens}")

async def main():
    # Test OpenAI
    os.environ["LLM_API_KEY"] = "your-key"
    await test_provider("openai")
    
    # Test vLLM (make sure server is running)
    os.environ["LLM_BASE_URL"] = "http://localhost:8000/v1"
    await test_provider("vllm")
    
    # Test Ollama (make sure it's running)
    await test_provider("ollama")

asyncio.run(main())
```

### ✅ Checkpoint
- [ ] I can switch between providers via environment variables
- [ ] I understand the provider abstraction pattern
- [ ] My application works with all three providers

---

## Phase 5: Fine-Tuning (Day 5-7)

### 📖 Read
- `docs/FINE_TUNING_GUIDE.md` - Complete guide
- `training/configs/character_chat_lora.yml` - Read comments

### 🔧 Exercise: Prepare Training Data

```python
# Run the data generator
python training/scripts/generate_training_data.py generate \
    --character sherlock_holmes \
    --num_examples 100 \
    --output training/data/sherlock_chat.jsonl

# Validate the data
python training/scripts/generate_training_data.py validate \
    --input training/data/sherlock_chat.jsonl
```

### 🔥 Exercise: Fine-Tune (If You Have GPU)

```bash
# Install Axolotl
pip install axolotl
pip install flash-attn --no-build-isolation

# Train!
accelerate launch -m axolotl.cli.train training/configs/character_chat_lora.yml

# Monitor in TensorBoard
tensorboard --logdir training/output/character-chat-lora
```

### ✅ Checkpoint
- [ ] I understand LoRA and why it works
- [ ] I can prepare training data
- [ ] I've fine-tuned a model (or understand the process)
- [ ] I know how to evaluate quality

---

## Phase 6: Production Optimization (Day 7-10)

### 📖 Read
- `app/llm/optimization.py` - Optimization techniques
- `app/llm/monitoring.py` - Monitoring and metrics

### 🔧 Exercise: Add Monitoring

```python
# Add monitoring to your chat endpoint
from app.llm.monitoring import get_metrics

metrics = get_metrics()

@app.post("/chat")
async def chat(request: ChatRequest):
    async with metrics.track_request_async(model="llama-8b") as tracker:
        # Process request
        result = await llm.chat(messages)
        
        # Record tokens
        tracker.set_tokens(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens
        )
        
        return result

# View metrics
metrics.print_summary(last_minutes=5)
```

### 🔧 Exercise: Set Up Grafana Dashboard

```bash
# Start monitoring stack
cd docker/vllm
docker-compose up -d

# Open Grafana at http://localhost:3001
# Login: admin / admin123
# View vLLM Performance Dashboard
```

### ✅ Checkpoint
- [ ] I'm tracking key metrics (latency, throughput, errors)
- [ ] I have a monitoring dashboard
- [ ] I understand optimization techniques

---

## Phase 7: Scaling (Day 10+)

### 📖 Read
- `docs/SELF_HOSTED_LLM_GUIDE.md` - Section 7: Scaling Strategies

### 🏗️ Architecture for Scale

```
                    ┌─────────────────────┐
                    │   Load Balancer     │
                    │   (nginx/HAProxy)   │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
    │   vLLM 1    │     │   vLLM 2    │     │   vLLM 3    │
    │   (GPU 0)   │     │   (GPU 1)   │     │   (GPU 2)   │
    └─────────────┘     └─────────────┘     └─────────────┘
```

### ✅ Final Checkpoint
- [ ] I understand horizontal scaling
- [ ] I know when to add more GPUs
- [ ] I have a plan for growth

---

## 🎯 Key Takeaways

1. **Start with Ollama** for development
2. **Graduate to vLLM** for production
3. **Monitor everything** - tokens, latency, errors
4. **Fine-tune** only when base model isn't good enough
5. **Scale horizontally** by adding more GPU instances

## 📚 Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)
- [Axolotl Fine-Tuning](https://github.com/OpenAccess-AI-Collective/axolotl)
- [LLM Leaderboard](https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard)

---

## 🏆 Completion Certificate

Once you've completed all checkpoints:

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   🎓 CERTIFICATE OF COMPLETION                                    ║
║                                                                    ║
║   This certifies that ____________________                        ║
║   has completed the Self-Hosted LLM Learning Roadmap              ║
║                                                                    ║
║   Skills acquired:                                                 ║
║   ✓ LLM Economics & Cost Analysis                                 ║
║   ✓ Model Selection & Evaluation                                  ║
║   ✓ vLLM Deployment & Configuration                               ║
║   ✓ Fine-Tuning with LoRA/QLoRA                                  ║
║   ✓ Production Monitoring & Optimization                          ║
║   ✓ Scaling Strategies                                            ║
║                                                                    ║
║   Date: _______________                                            ║
║                                                                    ║
╚═══════════════════════════════════════════════════════════════════╝
```

