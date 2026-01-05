"""
Base LLM Provider Interface
===========================

Abstract base classes that ALL LLM providers must implement.
This follows the Liskov Substitution Principle - any provider
can be swapped without changing application code.

Key Concepts:
    - Sync and async interfaces
    - Streaming support
    - Token counting
    - Error handling
"""

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator, Dict, Any
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """Chat message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A single chat message."""
    role: MessageRole
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class GenerationConfig:
    """
    Configuration for text generation.
    
    These parameters control HOW the model generates text.
    Understanding these is crucial for production LLM systems.
    """
    # Temperature: Controls randomness
    # 0.0 = deterministic (always pick most likely token)
    # 1.0 = balanced
    # 2.0 = very random
    # For character chat: 0.7-0.9 (creative but coherent)
    temperature: float = 0.7
    
    # Top-p (nucleus sampling): Only consider tokens with cumulative probability <= top_p
    # 0.9 = consider top 90% probability mass
    # Lower = more focused, higher = more diverse
    top_p: float = 0.9
    
    # Top-k: Only consider top k most likely tokens
    # 50 is a good default
    # Lower = more focused, higher = more diverse
    top_k: int = 50
    
    # Max tokens: Maximum response length
    # Set based on your use case (chat usually 500-2000)
    max_tokens: int = 2048
    
    # Stop sequences: Stop generation when these appear
    stop_sequences: Optional[List[str]] = None
    
    # Presence penalty: Penalize tokens that have appeared
    # Encourages talking about new topics
    presence_penalty: float = 0.0
    
    # Frequency penalty: Penalize tokens by their frequency
    # Reduces repetition
    frequency_penalty: float = 0.0
    
    # Repetition penalty: Another way to reduce repetition
    # 1.0 = no penalty, 1.2 = moderate penalty
    repetition_penalty: float = 1.0


@dataclass
class GenerationResult:
    """Result from text generation."""
    text: str
    finish_reason: str  # "stop", "length", "error"
    usage: Optional[Dict[str, int]] = None  # token counts
    
    @property
    def prompt_tokens(self) -> int:
        return self.usage.get("prompt_tokens", 0) if self.usage else 0
    
    @property
    def completion_tokens(self) -> int:
        return self.usage.get("completion_tokens", 0) if self.usage else 0
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", 0) if self.usage else 0


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers (OpenAI, vLLM, Ollama) must implement these methods.
    This allows your application to switch providers without code changes.
    
    Example:
        llm = get_llm()  # Could be any provider
        response = await llm.generate("Hello!")
        
        # Or with messages
        messages = [
            Message(MessageRole.SYSTEM, "You are Batman"),
            Message(MessageRole.USER, "Who are you?")
        ]
        response = await llm.chat(messages)
    """
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name/identifier."""
        pass
    
    @property
    @abstractmethod
    def context_length(self) -> int:
        """Return the model's context window size."""
        pass
    
    # ─────────────────────────────────────────────────────────────────
    # Core Generation Methods
    # ─────────────────────────────────────────────────────────────────
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The input prompt
            config: Generation configuration
            
        Returns:
            GenerationResult with text and metadata
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate a chat response.
        
        Args:
            messages: List of conversation messages
            config: Generation configuration
            
        Returns:
            GenerationResult with assistant's response
        """
        pass
    
    # ─────────────────────────────────────────────────────────────────
    # Streaming Methods
    # ─────────────────────────────────────────────────────────────────
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation token by token.
        
        Args:
            prompt: The input prompt
            config: Generation configuration
            
        Yields:
            Tokens/chunks as they're generated
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response token by token.
        
        Args:
            messages: List of conversation messages
            config: Generation configuration
            
        Yields:
            Tokens/chunks as they're generated
        """
        pass
    
    # ─────────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────────
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Important for:
        - Staying within context window
        - Cost estimation
        - Response length planning
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is healthy.
        
        Returns:
            True if service is responding
        """
        pass
    
    # ─────────────────────────────────────────────────────────────────
    # Convenience Methods (Implemented)
    # ─────────────────────────────────────────────────────────────────
    
    async def invoke(self, prompt: str) -> str:
        """Simple invoke that returns just the text."""
        result = await self.generate(prompt)
        return result.text
    
    async def ainvoke(self, prompt: str) -> str:
        """Alias for invoke (async)."""
        return await self.invoke(prompt)
    
    def fits_in_context(self, text: str, reserve: int = 1000) -> bool:
        """Check if text fits in context window with reserve for response."""
        return self.count_tokens(text) <= (self.context_length - reserve)


class BaseEmbeddings(ABC):
    """
    Abstract base class for embedding providers.
    
    Embeddings convert text into vectors for semantic search.
    Used for:
    - RAG retrieval
    - Memory search
    - Similarity matching
    """
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (embedding vector)
        """
        pass
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents.
        
        More efficient than calling embed_query multiple times.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query."""
        pass
    
    @abstractmethod
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents."""
        pass

