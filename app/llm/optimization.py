"""
LLM Optimization Techniques
===========================

Practical optimizations for production LLM serving.

LEARNING NOTES:

Why optimize?
    - Lower latency = Better UX
    - Higher throughput = More users per GPU
    - Lower cost = Better margins

Key techniques covered:
    1. Prompt caching - Reuse common prefixes
    2. Response streaming - Show tokens as generated
    3. Batching - Process multiple requests together
    4. Quantization - Reduce model precision
    5. Speculative decoding - Use draft model

Usage:
    from app.llm.optimization import CachedLLM, StreamingWrapper
    
    llm = CachedLLM(base_llm)
    response = await llm.generate(prompt)  # Caches common prefixes
"""

import asyncio
import hashlib
from typing import Optional, List, Dict, Any, AsyncGenerator
from functools import lru_cache
from dataclasses import dataclass
from collections import OrderedDict
import time
from .providers.base import BaseLLM, Message, GenerationConfig, GenerationResult


# ─────────────────────────────────────────────────────────────────────────────
# 1. Prompt Caching
# ─────────────────────────────────────────────────────────────────────────────

class PromptCache:
    """
    Cache for prompt prefixes.
    
    In character chat, system prompts are often repeated.
    We can cache the KV cache state for these prefixes.
    
    How it works:
        1. Hash the system prompt + character description
        2. If seen before, skip re-processing those tokens
        3. Only process the new user message
    
    Savings: 50-90% for repeated conversations with same character
    
    Note: This is a simplified version. vLLM has built-in prefix caching.
    """
    
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _hash_prefix(self, prefix: str) -> str:
        """Hash a prefix string."""
        return hashlib.sha256(prefix.encode()).hexdigest()[:16]
    
    def get(self, prefix: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a prefix."""
        key = self._hash_prefix(prefix)
        if key in self._cache:
            self._hits += 1
            # Move to end (LRU)
            self._cache.move_to_end(key)
            return self._cache[key]
        self._misses += 1
        return None
    
    def set(self, prefix: str, data: Dict[str, Any]):
        """Cache data for a prefix."""
        key = self._hash_prefix(prefix)
        self._cache[key] = data
        self._cache.move_to_end(key)
        
        # Evict oldest if over capacity
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
    
    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0


class CachedLLM(BaseLLM):
    """
    LLM wrapper with prompt caching.
    
    For character chat:
        - System prompt (character description) is cached
        - Only new messages need full processing
    
    Usage:
        base_llm = VLLMProvider(...)
        cached_llm = CachedLLM(base_llm)
        
        # First call - processes everything
        response = await cached_llm.chat(messages)
        
        # Second call with same character - cache hit!
        response = await cached_llm.chat(messages)
    """
    
    def __init__(self, base_llm: BaseLLM, cache_size: int = 100):
        self._base = base_llm
        self._cache = PromptCache(max_size=cache_size)
    
    @property
    def model_name(self) -> str:
        return self._base.model_name
    
    @property
    def context_length(self) -> int:
        return self._base.context_length
    
    def _extract_cacheable_prefix(self, messages: List[Message]) -> str:
        """Extract the cacheable prefix (system + initial context)."""
        prefix_parts = []
        for msg in messages:
            if msg.role.value == "system":
                prefix_parts.append(f"system:{msg.content}")
            else:
                break  # Stop at first non-system message
        return "|".join(prefix_parts)
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Generate with caching (delegates to chat)."""
        return await self._base.generate(prompt, config)
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Chat with prefix caching.
        
        Note: This is a conceptual implementation.
        For true KV cache reuse, you need vLLM's prefix caching.
        """
        prefix = self._extract_cacheable_prefix(messages)
        cached = self._cache.get(prefix)
        
        if cached:
            # In a real implementation, we'd pass the cached KV state
            # For now, we just log the hit
            pass
        
        result = await self._base.chat(messages, config)
        
        # Cache for next time
        self._cache.set(prefix, {"timestamp": time.time()})
        
        return result
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._base.generate_stream(prompt, config):
            yield chunk
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._base.chat_stream(messages, config):
            yield chunk
    
    def count_tokens(self, text: str) -> int:
        return self._base.count_tokens(text)
    
    async def health_check(self) -> bool:
        return await self._base.health_check()
    
    @property
    def cache_hit_rate(self) -> float:
        return self._cache.hit_rate


# ─────────────────────────────────────────────────────────────────────────────
# 2. Response Caching
# ─────────────────────────────────────────────────────────────────────────────

class ResponseCache:
    """
    Cache full responses for identical requests.
    
    When to use:
        - Deterministic responses (temperature=0)
        - Repeated questions
        - Testing/development
    
    When NOT to use:
        - Creative/varied responses
        - Time-sensitive content
        - User-specific data
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: Dict[str, tuple] = {}  # key -> (response, timestamp)
        self._max_size = max_size
        self._ttl = ttl_seconds
    
    def _hash_request(self, messages: List[Message], config: GenerationConfig) -> str:
        """Create a hash of the request."""
        content = json.dumps({
            "messages": [m.to_dict() for m in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, messages: List[Message], config: GenerationConfig) -> Optional[str]:
        """Get cached response."""
        key = self._hash_request(messages, config)
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return response
            else:
                del self._cache[key]  # Expired
        return None
    
    def set(self, messages: List[Message], config: GenerationConfig, response: str):
        """Cache a response."""
        if len(self._cache) >= self._max_size:
            # Remove oldest entries
            sorted_keys = sorted(self._cache.keys(), 
                               key=lambda k: self._cache[k][1])
            for k in sorted_keys[:len(sorted_keys)//2]:
                del self._cache[k]
        
        key = self._hash_request(messages, config)
        self._cache[key] = (response, time.time())


import json  # Need this for ResponseCache


# ─────────────────────────────────────────────────────────────────────────────
# 3. Request Batching
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PendingRequest:
    """A request waiting to be batched."""
    messages: List[Message]
    config: GenerationConfig
    future: asyncio.Future


class BatchingLLM(BaseLLM):
    """
    LLM wrapper that batches multiple requests.
    
    How it works:
        1. Incoming requests are queued
        2. After a short delay (or when batch is full), process together
        3. vLLM handles the actual batching, this just groups requests
    
    Benefits:
        - Better GPU utilization
        - Higher throughput under load
    
    Trade-offs:
        - Adds latency (wait for batch)
        - More complex than direct calls
    
    When to use:
        - High-traffic scenarios
        - When throughput > latency
    """
    
    def __init__(
        self,
        base_llm: BaseLLM,
        max_batch_size: int = 8,
        max_wait_ms: int = 50,
    ):
        self._base = base_llm
        self._max_batch_size = max_batch_size
        self._max_wait_ms = max_wait_ms
        self._pending: List[PendingRequest] = []
        self._lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
    
    @property
    def model_name(self) -> str:
        return self._base.model_name
    
    @property
    def context_length(self) -> int:
        return self._base.context_length
    
    async def _process_batch(self):
        """Process accumulated requests as a batch."""
        await asyncio.sleep(self._max_wait_ms / 1000)
        
        async with self._lock:
            if not self._pending:
                return
            
            batch = self._pending[:self._max_batch_size]
            self._pending = self._pending[self._max_batch_size:]
        
        # Process each request
        # In a true batching scenario, vLLM would batch these internally
        for req in batch:
            try:
                result = await self._base.chat(req.messages, req.config)
                req.future.set_result(result)
            except Exception as e:
                req.future.set_exception(e)
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Queue request for batching."""
        config = config or GenerationConfig()
        future = asyncio.Future()
        
        async with self._lock:
            self._pending.append(PendingRequest(messages, config, future))
            
            # Start batch processing if this is the first request
            if len(self._pending) == 1:
                self._batch_task = asyncio.create_task(self._process_batch())
            # Or process immediately if batch is full
            elif len(self._pending) >= self._max_batch_size:
                if self._batch_task:
                    self._batch_task.cancel()
                self._batch_task = asyncio.create_task(self._process_batch())
        
        return await future
    
    # Delegate other methods
    async def generate(self, prompt: str, config: Optional[GenerationConfig] = None) -> GenerationResult:
        return await self._base.generate(prompt, config)
    
    async def generate_stream(self, prompt: str, config: Optional[GenerationConfig] = None) -> AsyncGenerator[str, None]:
        async for chunk in self._base.generate_stream(prompt, config):
            yield chunk
    
    async def chat_stream(self, messages: List[Message], config: Optional[GenerationConfig] = None) -> AsyncGenerator[str, None]:
        async for chunk in self._base.chat_stream(messages, config):
            yield chunk
    
    def count_tokens(self, text: str) -> int:
        return self._base.count_tokens(text)
    
    async def health_check(self) -> bool:
        return await self._base.health_check()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Smart Retries
# ─────────────────────────────────────────────────────────────────────────────

class RetryingLLM(BaseLLM):
    """
    LLM wrapper with smart retry logic.
    
    Handles:
        - Transient failures (network issues)
        - Rate limiting (with backoff)
        - Server errors
    
    Does NOT retry:
        - Invalid requests
        - Authentication errors
        - Context length exceeded
    """
    
    RETRYABLE_ERRORS = {
        "rate_limit",
        "server_error",
        "timeout",
        "connection",
    }
    
    def __init__(
        self,
        base_llm: BaseLLM,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self._base = base_llm
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
    
    @property
    def model_name(self) -> str:
        return self._base.model_name
    
    @property
    def context_length(self) -> int:
        return self._base.context_length
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in self.RETRYABLE_ERRORS)
    
    async def _with_retry(self, func, *args, **kwargs):
        """Execute function with retries."""
        last_error = None
        
        for attempt in range(self._max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self._should_retry(e):
                    raise
                
                if attempt < self._max_retries - 1:
                    # Exponential backoff with jitter
                    delay = min(
                        self._base_delay * (2 ** attempt),
                        self._max_delay
                    )
                    delay *= (0.5 + 0.5 * (hash(str(e)) % 100) / 100)  # Jitter
                    await asyncio.sleep(delay)
        
        raise last_error
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        return await self._with_retry(self._base.chat, messages, config)
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        return await self._with_retry(self._base.generate, prompt, config)
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        # Streaming doesn't retry mid-stream
        async for chunk in self._base.generate_stream(prompt, config):
            yield chunk
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._base.chat_stream(messages, config):
            yield chunk
    
    def count_tokens(self, text: str) -> int:
        return self._base.count_tokens(text)
    
    async def health_check(self) -> bool:
        return await self._base.health_check()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fallback Chain
# ─────────────────────────────────────────────────────────────────────────────

class FallbackLLM(BaseLLM):
    """
    LLM with fallback providers.
    
    Use case:
        Primary: Self-hosted vLLM (cheap)
        Fallback: OpenAI (reliable)
    
    Falls back when:
        - Primary is down
        - Primary is too slow
        - Primary returns errors
    """
    
    def __init__(
        self,
        primary: BaseLLM,
        fallback: BaseLLM,
        timeout_ms: int = 10000,
    ):
        self._primary = primary
        self._fallback = fallback
        self._timeout = timeout_ms / 1000
        self._fallback_count = 0
    
    @property
    def model_name(self) -> str:
        return f"{self._primary.model_name} (fallback: {self._fallback.model_name})"
    
    @property
    def context_length(self) -> int:
        return min(self._primary.context_length, self._fallback.context_length)
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        try:
            return await asyncio.wait_for(
                self._primary.chat(messages, config),
                timeout=self._timeout
            )
        except (asyncio.TimeoutError, Exception) as e:
            self._fallback_count += 1
            return await self._fallback.chat(messages, config)
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        try:
            return await asyncio.wait_for(
                self._primary.generate(prompt, config),
                timeout=self._timeout
            )
        except (asyncio.TimeoutError, Exception):
            self._fallback_count += 1
            return await self._fallback.generate(prompt, config)
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        # Try primary, fallback on first error
        try:
            async for chunk in self._primary.generate_stream(prompt, config):
                yield chunk
        except Exception:
            self._fallback_count += 1
            async for chunk in self._fallback.generate_stream(prompt, config):
                yield chunk
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            async for chunk in self._primary.chat_stream(messages, config):
                yield chunk
        except Exception:
            self._fallback_count += 1
            async for chunk in self._fallback.chat_stream(messages, config):
                yield chunk
    
    def count_tokens(self, text: str) -> int:
        return self._primary.count_tokens(text)
    
    async def health_check(self) -> bool:
        return await self._primary.health_check() or await self._fallback.health_check()
    
    @property
    def fallback_percentage(self) -> float:
        """Percentage of requests that fell back."""
        # This would need request counting to be accurate
        return self._fallback_count

