"""
LLM Factory
===========

Factory pattern for creating LLM and embedding providers.

This is the ONLY place where you decide which provider to use.
Application code just calls get_llm() and get_embeddings().

Why Factory Pattern?
    - Single place to configure providers
    - Easy to switch providers
    - Dependency injection ready
    - Testable (mock the factory)

Usage:
    from app.llm import get_llm, get_embeddings
    
    # Get configured provider (reads from environment)
    llm = get_llm()
    embeddings = get_embeddings()
    
    # Or specify provider explicitly
    llm = get_llm(provider="vllm")
"""

from functools import lru_cache
from typing import Optional
from .config import (
    LLMProvider, EmbeddingProvider,
    get_llm_config, get_embedding_config
)
from .providers.base import BaseLLM, BaseEmbeddings


@lru_cache(maxsize=1)
def get_llm(provider: Optional[str] = None) -> BaseLLM:
    """
    Get the configured LLM provider.
    
    The provider is determined by:
    1. Explicit `provider` argument
    2. LLM_PROVIDER environment variable
    3. Default: "openai"
    
    Args:
        provider: Optional provider override ("openai", "vllm", "ollama")
        
    Returns:
        Configured LLM provider instance
        
    Example:
        # Use default provider
        llm = get_llm()
        response = await llm.chat(messages)
        
        # Force vLLM
        llm = get_llm(provider="vllm")
    """
    config = get_llm_config()
    
    # Allow override
    if provider:
        selected_provider = LLMProvider(provider.lower())
    else:
        selected_provider = config.provider
    
    # Create provider instance
    if selected_provider == LLMProvider.OPENAI:
        from .providers.openai_provider import OpenAILLM
        return OpenAILLM(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url if "openai" not in config.base_url else None,
        )
    
    elif selected_provider == LLMProvider.VLLM:
        from .providers.vllm_provider import VLLMProvider
        return VLLMProvider(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            timeout=config.timeout,
        )
    
    elif selected_provider == LLMProvider.OLLAMA:
        from .providers.ollama_provider import OllamaProvider
        return OllamaProvider(
            base_url=config.base_url,
            model=config.model,
            timeout=config.timeout,
        )
    
    else:
        raise ValueError(f"Unknown LLM provider: {selected_provider}")


@lru_cache(maxsize=1)
def get_embeddings(provider: Optional[str] = None) -> BaseEmbeddings:
    """
    Get the configured embeddings provider.
    
    Args:
        provider: Optional provider override
        
    Returns:
        Configured embeddings provider instance
    """
    config = get_embedding_config()
    
    if provider:
        selected_provider = EmbeddingProvider(provider.lower())
    else:
        selected_provider = config.provider
    
    if selected_provider == EmbeddingProvider.OPENAI:
        from .providers.openai_provider import OpenAIEmbeddings
        return OpenAIEmbeddings(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
        )
    
    elif selected_provider == EmbeddingProvider.VLLM:
        from .providers.vllm_provider import VLLMEmbeddings
        return VLLMEmbeddings(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
        )
    
    elif selected_provider == EmbeddingProvider.LOCAL:
        from .providers.ollama_provider import OllamaEmbeddings
        return OllamaEmbeddings(
            base_url=config.base_url or "http://localhost:11434",
            model=config.model,
        )
    
    else:
        raise ValueError(f"Unknown embedding provider: {selected_provider}")


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions for Direct Use
# ─────────────────────────────────────────────────────────────────────────────

async def chat(messages: list, **kwargs) -> str:
    """
    Quick chat without managing provider.
    
    Usage:
        from app.llm.factory import chat
        
        response = await chat([
            {"role": "system", "content": "You are Batman"},
            {"role": "user", "content": "Who are you?"}
        ])
    """
    from .providers.base import Message, MessageRole, GenerationConfig
    
    llm = get_llm()
    
    # Convert dicts to Message objects
    msg_objects = []
    for m in messages:
        role = MessageRole(m["role"])
        msg_objects.append(Message(role=role, content=m["content"]))
    
    # Create config from kwargs
    config = GenerationConfig(
        temperature=kwargs.get("temperature", 0.7),
        max_tokens=kwargs.get("max_tokens", 2048),
        top_p=kwargs.get("top_p", 0.9),
    )
    
    result = await llm.chat(msg_objects, config)
    return result.text


async def embed(text: str) -> list:
    """
    Quick embedding without managing provider.
    
    Usage:
        from app.llm.factory import embed
        
        vector = await embed("Hello world")
    """
    embeddings = get_embeddings()
    return await embeddings.aembed_query(text)


def clear_cache():
    """Clear cached provider instances (useful for testing)."""
    get_llm.cache_clear()
    get_embeddings.cache_clear()

