"""
LLM Configuration
=================

Centralized configuration for all LLM providers.

Environment Variables:
    LLM_PROVIDER: "openai" | "vllm" | "ollama"
    LLM_MODEL: Model name/path
    LLM_BASE_URL: API endpoint (for vLLM/Ollama)
    
    EMBEDDING_PROVIDER: "openai" | "local"
    EMBEDDING_MODEL: Model name
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from functools import lru_cache


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    VLLM = "vllm"
    OLLAMA = "ollama"
    # Future: TGI, llama.cpp, etc.


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    LOCAL = "local"  # sentence-transformers
    VLLM = "vllm"


@dataclass
class LLMConfig:
    """
    LLM provider configuration.
    
    Attributes:
        provider: Which LLM backend to use
        model: Model name or HuggingFace path
        base_url: API endpoint (for self-hosted)
        api_key: API key (for OpenAI)
        temperature: Generation temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout in seconds
    """
    provider: LLMProvider
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    
    # vLLM specific
    tensor_parallel_size: int = 1  # Number of GPUs
    max_model_len: int = 8192      # Context window
    gpu_memory_utilization: float = 0.90
    
    # Performance tuning
    enable_streaming: bool = True
    enable_caching: bool = True


@dataclass
class EmbeddingConfig:
    """Embedding provider configuration."""
    provider: EmbeddingProvider
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    dimensions: int = 1536
    batch_size: int = 32


@lru_cache()
def get_llm_config() -> LLMConfig:
    """
    Get LLM configuration from environment.
    
    Returns:
        LLMConfig with provider settings
    """
    provider_str = os.getenv("LLM_PROVIDER", "openai").lower()
    
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        raise ValueError(f"Unknown LLM provider: {provider_str}. "
                        f"Supported: {[p.value for p in LLMProvider]}")
    
    # Default models per provider
    default_models = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.VLLM: "meta-llama/Llama-3.1-8B-Instruct",
        LLMProvider.OLLAMA: "llama3.1:8b",
    }
    
    def _in_docker() -> bool:
        # Standard: /.dockerenv exists inside Docker containers
        return os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER", "").lower() in ("1", "true", "yes")

    def _rewrite_localhost_for_docker(url: str) -> str:
        """
        If a self-hosted base_url is set to localhost inside Docker, it won't reach the host.
        Rewrite to host.docker.internal automatically for a smoother env-driven experience.
        """
        if not url:
            return url
        if not _in_docker():
            return url
        return url.replace("://localhost", "://host.docker.internal").replace("://127.0.0.1", "://host.docker.internal")

    # Default base URLs (docker-smart for self-hosted providers)
    default_urls = {
        LLMProvider.OPENAI: "https://api.openai.com/v1",
        LLMProvider.VLLM: "http://host.docker.internal:8000/v1" if _in_docker() else "http://localhost:8000/v1",
        LLMProvider.OLLAMA: "http://host.docker.internal:11434" if _in_docker() else "http://localhost:11434",
    }
    base_url = _rewrite_localhost_for_docker(os.getenv("LLM_BASE_URL", default_urls[provider]))
    
    return LLMConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", default_models[provider]),
        base_url=base_url,
        api_key=os.getenv("LLM_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        tensor_parallel_size=int(os.getenv("VLLM_TENSOR_PARALLEL", "1")),
        max_model_len=int(os.getenv("VLLM_MAX_MODEL_LEN", "8192")),
        gpu_memory_utilization=float(os.getenv("VLLM_GPU_MEMORY", "0.90")),
        enable_streaming=os.getenv("LLM_STREAMING", "true").lower() == "true",
        enable_caching=os.getenv("LLM_CACHING", "true").lower() == "true",
    )


@lru_cache()
def get_embedding_config() -> EmbeddingConfig:
    """Get embedding configuration from environment."""
    provider_str = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    
    try:
        provider = EmbeddingProvider(provider_str)
    except ValueError:
        raise ValueError(f"Unknown embedding provider: {provider_str}")
    
    # Default models per provider
    default_models = {
        EmbeddingProvider.OPENAI: "text-embedding-3-small",
        EmbeddingProvider.LOCAL: "BAAI/bge-small-en-v1.5",
        EmbeddingProvider.VLLM: "BAAI/bge-small-en-v1.5",
    }
    
    # Dimensions per model
    dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
    }
    
    def _in_docker() -> bool:
        return os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER", "").lower() in ("1", "true", "yes")

    def _rewrite_localhost_for_docker(url: Optional[str]) -> Optional[str]:
        if not url:
            return url
        if not _in_docker():
            return url
        return url.replace("://localhost", "://host.docker.internal").replace("://127.0.0.1", "://host.docker.internal")

    model = os.getenv("EMBEDDING_MODEL", default_models[provider])
    base_url = _rewrite_localhost_for_docker(os.getenv("EMBEDDING_BASE_URL"))
    
    return EmbeddingConfig(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY")),
        dimensions=int(os.getenv("VECTOR_SIZE", dimensions.get(model, 1536))),
        batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
    )

