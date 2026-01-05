"""
OpenAI Provider
===============

OpenAI API provider for LLM and embeddings.

Kept for:
    - Backward compatibility with existing code
    - Fallback when self-hosted is unavailable
    - Baseline quality comparison

Cost Awareness:
    GPT-4o-mini: $0.15/1M input, $0.60/1M output
    GPT-4o: $2.50/1M input, $10/1M output
    Embeddings: $0.02/1M tokens
    
    At scale, this adds up fast. See SELF_HOSTED_LLM_GUIDE.md
"""

import os
import openai
from openai import AsyncOpenAI, OpenAI
from typing import List, Optional, AsyncGenerator
import tiktoken
from .base import (
    BaseLLM, BaseEmbeddings,
    Message, MessageRole, GenerationConfig, GenerationResult
)


class OpenAILLM(BaseLLM):
    """
    OpenAI API provider.
    
    This is what you've been using. Now compare with self-hosted options.
    """
    
    MODEL_CONTEXT_LENGTHS = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16384,
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._base_url = base_url
        
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        
        self._sync_client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        
        # Token counting
        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def context_length(self) -> int:
        return self.MODEL_CONTEXT_LENGTHS.get(self._model, 8192)
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Generate completion (converts to chat format internally)."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        return await self.chat(messages, config)
    
    async def chat(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Generate chat completion."""
        config = config or GenerationConfig()
        
        messages_dicts = [m.to_dict() for m in messages]
        
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages_dicts,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            presence_penalty=config.presence_penalty,
            frequency_penalty=config.frequency_penalty,
            stop=config.stop_sequences,
        )
        
        choice = response.choices[0]
        
        return GenerationResult(
            text=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
        )
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generation."""
        messages = [Message.from_dict({"role": "user", "content": prompt})]
        async for chunk in self.chat_stream(messages, config):
            yield chunk
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        config = config or GenerationConfig()
        
        messages_dicts = [m.to_dict() for m in messages]
        
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages_dicts,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            presence_penalty=config.presence_penalty,
            frequency_penalty=config.frequency_penalty,
            stop=config.stop_sequences,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken (accurate for OpenAI models)."""
        return len(self._encoding.encode(text))
    
    async def health_check(self) -> bool:
        """Check OpenAI API availability."""
        try:
            # List models as a simple health check
            await self._client.models.list()
            return True
        except Exception:
            return False


class OpenAIEmbeddings(BaseEmbeddings):
    """
    OpenAI embeddings.
    
    Models:
        text-embedding-3-small: 1536 dims, $0.02/1M tokens
        text-embedding-3-large: 3072 dims, $0.13/1M tokens
        text-embedding-ada-002: 1536 dims, $0.10/1M tokens (legacy)
    """
    
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=base_url,
        )
        
        self._sync_client = OpenAI(
            api_key=self._api_key,
            base_url=base_url,
        )
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def dimensions(self) -> int:
        return self.MODEL_DIMENSIONS.get(self._model, 1536)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed single text."""
        response = self._sync_client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        response = self._sync_client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]
    
    async def aembed_query(self, text: str) -> List[float]:
        """Async embed single text."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async embed multiple texts."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]

