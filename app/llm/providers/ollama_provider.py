"""
Ollama Provider
===============

Local development LLM provider using Ollama.

Ollama is perfect for development because:
    - Easy setup (one command)
    - Runs on consumer hardware
    - No API keys needed
    - Great for testing and iteration

Production vs Development:
    Development: Ollama (simple, local)
    Production: vLLM (high throughput, optimized)

Usage:
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Pull a model
    ollama pull llama3.1:8b
    
    # Start serving (happens automatically)
    ollama serve
    
    # Use in code
    from app.llm.providers.ollama_provider import OllamaProvider
    
    llm = OllamaProvider(model="llama3.1:8b")
    response = await llm.generate("Hello!")
"""

import httpx
import json
from typing import List, Optional, AsyncGenerator, Dict, Any
from .base import (
    BaseLLM, BaseEmbeddings,
    Message, MessageRole, GenerationConfig, GenerationResult
)


class OllamaProvider(BaseLLM):
    """
    Ollama provider for local LLM inference.
    
    Ollama uses its own API format, not OpenAI compatible.
    This provider handles the translation.
    
    Key differences from vLLM:
        - Simpler setup (just ollama pull <model>)
        - Lower throughput (single-request optimized)
        - Easier model management
        - Better for development/testing
    """
    
    # Ollama model names and their context lengths
    MODEL_CONTEXT_LENGTHS = {
        "llama3.1:8b": 128000,
        "llama3.1:70b": 128000,
        "llama3.1:8b-instruct-q4_0": 128000,
        "mistral:7b": 32768,
        "mixtral:8x7b": 32768,
        "qwen2.5:7b": 131072,
        "codellama:7b": 16384,
        "phi3:mini": 4096,
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: int = 120,  # Ollama can be slow on first request
    ):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama server URL (default localhost:11434)
            model: Model name (e.g., llama3.1:8b)
            timeout: Request timeout (first request loads model, can be slow)
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
        )
        
        self._sync_client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
        )
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def context_length(self) -> int:
        # Try to match model name patterns
        for pattern, length in self.MODEL_CONTEXT_LENGTHS.items():
            if pattern in self._model:
                return length
        return 8192  # Conservative default
    
    # ─────────────────────────────────────────────────────────────────
    # Core Generation
    # ─────────────────────────────────────────────────────────────────
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate text completion using Ollama's /api/generate endpoint.
        """
        config = config or GenerationConfig()
        
        # Ollama uses different parameter names
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repetition_penalty,
            }
        }
        
        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences
        
        response = await self._client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return GenerationResult(
            text=data.get("response", ""),
            finish_reason="stop" if data.get("done") else "length",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
        )
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate chat completion using Ollama's /api/chat endpoint.
        """
        config = config or GenerationConfig()
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]
        
        payload = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repetition_penalty,
            }
        }
        
        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return GenerationResult(
            text=data.get("message", {}).get("content", ""),
            finish_reason="stop" if data.get("done") else "length",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
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
        Stream text generation.
        
        Ollama streams as newline-delimited JSON.
        """
        config = config or GenerationConfig()
        
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": config.max_tokens,
                "temperature": config.temperature,
            }
        }
        
        async with self._client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        text = data.get("response", "")
                        if text:
                            yield text
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        config = config or GenerationConfig()
        
        ollama_messages = [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]
        
        payload = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "num_predict": config.max_tokens,
                "temperature": config.temperature,
            }
        }
        
        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    # ─────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count (4 chars per token approximation)."""
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            
            # Check if our model is available
            model_names = [m["name"] for m in data.get("models", [])]
            
            if self._model in model_names:
                return True
            
            # Check for partial match (e.g., "llama3.1:8b" matches "llama3.1:8b-instruct")
            for name in model_names:
                if self._model in name or name in self._model:
                    return True
            
            print(f"Warning: Model {self._model} not found. Available: {model_names}")
            return False
            
        except Exception as e:
            print(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """List available models."""
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama library.
        
        This can take a while for large models.
        """
        try:
            response = await self._client.post(
                "/api/pull",
                json={"name": model},
                timeout=600  # 10 minutes for large models
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to pull model: {e}")
            return False
    
    async def close(self):
        """Close HTTP clients."""
        await self._client.aclose()
        self._sync_client.close()


class OllamaEmbeddings(BaseEmbeddings):
    """
    Embeddings using Ollama's embedding endpoint.
    
    Usage:
        ollama pull nomic-embed-text
        
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vector = embeddings.embed_query("Hello world")
    """
    
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimensions_val = self.MODEL_DIMENSIONS.get(model, 768)
        
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30,
        )
        self._sync_client = httpx.Client(
            base_url=self._base_url,
            timeout=30,
        )
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def dimensions(self) -> int:
        return self._dimensions_val
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single text (synchronous)."""
        response = self._sync_client.post(
            "/api/embeddings",
            json={"model": self._model, "prompt": text}
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts (synchronous)."""
        # Ollama doesn't support batch embeddings, so we loop
        return [self.embed_query(text) for text in texts]
    
    async def aembed_query(self, text: str) -> List[float]:
        """Embed a single text (async)."""
        response = await self._client.post(
            "/api/embeddings",
            json={"model": self._model, "prompt": text}
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts (async)."""
        # Could use asyncio.gather for parallel processing
        import asyncio
        tasks = [self.aembed_query(text) for text in texts]
        return await asyncio.gather(*tasks)

