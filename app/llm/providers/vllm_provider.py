"""
vLLM Provider
=============

Production LLM provider using vLLM for high-throughput inference.

vLLM serves an OpenAI-compatible API, so we use httpx to call it.
This keeps the implementation simple and compatible.

Key vLLM Benefits:
    - PagedAttention for memory efficiency
    - Continuous batching for throughput
    - Tensor parallelism for large models
    - OpenAI API compatibility

Usage:
    # Start vLLM server
    python -m vllm.entrypoints.openai.api_server \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --port 8000
    
    # Use in code
    from app.llm.providers.vllm_provider import VLLMProvider
    
    llm = VLLMProvider(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-3.1-8B-Instruct"
    )
    response = await llm.generate("Hello!")
"""

import httpx
import json
from typing import List, Optional, AsyncGenerator, Dict, Any
from .base import (
    BaseLLM, BaseEmbeddings, 
    Message, GenerationConfig, GenerationResult
)


class VLLMProvider(BaseLLM):
    """
    vLLM provider for high-performance LLM inference.
    
    Connects to vLLM's OpenAI-compatible API server.
    
    Architecture:
        Your App → VLLMProvider → vLLM Server → GPU
        
    The vLLM server handles:
        - Batching multiple requests
        - KV cache management (PagedAttention)
        - GPU memory optimization
        - Request scheduling
    """
    
    # Default context lengths for common models
    MODEL_CONTEXT_LENGTHS = {
        "meta-llama/Llama-3.1-8B-Instruct": 128000,
        "meta-llama/Llama-3.1-70B-Instruct": 128000,
        "mistralai/Mistral-7B-Instruct-v0.2": 32768,
        "mistralai/Mixtral-8x7B-Instruct-v0.1": 32768,
        "Qwen/Qwen2.5-7B-Instruct": 131072,
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "meta-llama/Llama-3.1-8B-Instruct",
        api_key: Optional[str] = None,  # vLLM doesn't require API key by default
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """
        Initialize vLLM provider.
        
        Args:
            base_url: vLLM server URL (e.g., http://localhost:8000/v1)
            model: Model name (must match what vLLM is serving)
            api_key: Optional API key (if vLLM configured with auth)
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        
        # Configure HTTP client
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=timeout,
        )
        
        # Token counting (approximate for Llama tokenizer)
        # In production, use tiktoken or the model's tokenizer
        self._chars_per_token = 4  # Rough estimate
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def context_length(self) -> int:
        return self.MODEL_CONTEXT_LENGTHS.get(self._model, 8192)
    
    # ─────────────────────────────────────────────────────────────────
    # Core Generation
    # ─────────────────────────────────────────────────────────────────
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate text completion.
        
        Uses vLLM's /completions endpoint.
        """
        config = config or GenerationConfig()
        
        payload = {
            "model": self._model,
            "prompt": prompt,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "presence_penalty": config.presence_penalty,
            "frequency_penalty": config.frequency_penalty,
            "stream": False,
        }
        
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences
        
        response = await self._client.post("/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        
        choice = data["choices"][0]
        
        return GenerationResult(
            text=choice["text"],
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage"),
        )
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate chat completion.
        
        Uses vLLM's /chat/completions endpoint (OpenAI compatible).
        
        This is the main method you'll use for character chat.
        """
        config = config or GenerationConfig()
        
        # Convert messages to dicts
        messages_dicts = [m.to_dict() for m in messages]
        
        payload = {
            "model": self._model,
            "messages": messages_dicts,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "presence_penalty": config.presence_penalty,
            "frequency_penalty": config.frequency_penalty,
            "stream": False,
        }
        
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences
        
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        
        choice = data["choices"][0]
        
        return GenerationResult(
            text=choice["message"]["content"],
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage"),
        )
    
    # ─────────────────────────────────────────────────────────────────
    # Streaming
    # ─────────────────────────────────────────────────────────────────
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text completion.
        
        vLLM streams using Server-Sent Events (SSE) format.
        Each event contains a JSON chunk with the next token(s).
        """
        config = config or GenerationConfig()
        
        payload = {
            "model": self._model,
            "prompt": prompt,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True,
        }
        
        async with self._client.stream("POST", "/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        text = data["choices"][0].get("text", "")
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        continue
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion.
        
        This is what you'll use for streaming character responses.
        Tokens arrive as soon as they're generated by the model.
        
        Latency breakdown:
            Time to First Token (TTFT): ~100-500ms (model thinking)
            Inter-token latency: ~20-50ms (token generation)
            
        For character chat, streaming dramatically improves UX.
        """
        config = config or GenerationConfig()
        
        messages_dicts = [m.to_dict() for m in messages]
        
        payload = {
            "model": self._model,
            "messages": messages_dicts,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True,
        }
        
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    # ─────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        For production, use tiktoken or the model's actual tokenizer.
        This is a rough estimate (4 chars ≈ 1 token for English).
        
        Why this matters:
            - Context window limits
            - Cost estimation (for API providers)
            - Memory planning
        """
        # Rough estimate: 4 characters per token
        return len(text) // self._chars_per_token
    
    async def health_check(self) -> bool:
        """
        Check if vLLM server is healthy.
        
        vLLM provides a /health endpoint.
        Also check /models to verify the expected model is loaded.
        """
        try:
            # Check basic health
            response = await self._client.get("/models")
            response.raise_for_status()
            
            # Verify our model is available
            data = response.json()
            model_ids = [m["id"] for m in data.get("data", [])]
            
            if self._model in model_ids:
                return True
            
            print(f"Warning: Model {self._model} not found. Available: {model_ids}")
            return len(model_ids) > 0
            
        except Exception as e:
            print(f"vLLM health check failed: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        response = await self._client.get("/models")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class VLLMEmbeddings(BaseEmbeddings):
    """
    Embeddings using vLLM's embedding endpoint.
    
    vLLM can serve embedding models alongside LLMs.
    Useful for keeping everything self-hosted.
    
    Usage:
        # Start vLLM with embedding model
        python -m vllm.entrypoints.openai.api_server \
            --model BAAI/bge-small-en-v1.5 \
            --port 8001
    """
    
    MODEL_DIMENSIONS = {
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001/v1",
        model: str = "BAAI/bge-small-en-v1.5",
        api_key: Optional[str] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimensions_val = self.MODEL_DIMENSIONS.get(model, 384)
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=30,
        )
        
        # Sync client for non-async methods
        self._sync_client = httpx.Client(
            base_url=self._base_url,
            headers=headers,
            timeout=30,
        )
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def dimensions(self) -> int:
        return self._dimensions_val
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query (synchronous)."""
        response = self._sync_client.post(
            "/embeddings",
            json={"model": self._model, "input": text}
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (synchronous)."""
        response = self._sync_client.post(
            "/embeddings",
            json={"model": self._model, "input": texts}
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
    
    async def aembed_query(self, text: str) -> List[float]:
        """Embed a single query (async)."""
        response = await self._client.post(
            "/embeddings",
            json={"model": self._model, "input": text}
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (async)."""
        response = await self._client.post(
            "/embeddings",
            json={"model": self._model, "input": texts}
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

