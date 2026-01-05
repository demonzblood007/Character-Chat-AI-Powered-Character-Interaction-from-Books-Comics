"""
LLM Module
==========

Abstraction layer for LLM providers.
Supports both cloud APIs (OpenAI) and self-hosted (vLLM, Ollama).

Usage:
    from app.llm import get_llm, get_embeddings
    
    llm = get_llm()  # Returns configured provider
    response = await llm.generate("Hello, Batman!")
"""

from .config import LLMConfig, get_llm_config
from .factory import get_llm, get_embeddings
from .providers.base import BaseLLM, BaseEmbeddings

__all__ = [
    "get_llm",
    "get_embeddings",
    "LLMConfig",
    "get_llm_config",
    "BaseLLM",
    "BaseEmbeddings",
]

