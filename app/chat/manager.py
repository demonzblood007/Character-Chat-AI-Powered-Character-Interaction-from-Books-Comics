"""
Chat Service Manager
====================

Singleton manager for ChatService with proper lifecycle management.
Integrates LLM providers, memory system, and monitoring.

This is the GLUE that connects everything together.
"""

import os
import asyncio
from typing import Optional
from functools import lru_cache

from .service import ChatService


class ChatServiceManager:
    """
    Manages the lifecycle of ChatService.
    
    Uses singleton pattern to ensure:
    - One set of database connections
    - One LLM provider instance
    - Proper initialization and cleanup
    
    Usage:
        # In FastAPI startup
        manager = ChatServiceManager()
        await manager.initialize()
        
        # Get service for requests
        service = manager.get_service()
        response = await service.chat(user_id, character, message)
        
        # In FastAPI shutdown
        await manager.shutdown()
    """
    
    _instance: Optional["ChatServiceManager"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._chat_service = None
            cls._instance._llm = None
            cls._instance._embeddings = None
        return cls._instance
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self):
        """
        Initialize the chat service with all dependencies.
        
        Called once during application startup.
        """
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            print("🔧 Initializing Chat Service...")
            
            # 1. Initialize LLM Provider
            print("  → Loading LLM provider...")
            self._llm = await self._create_llm()
            
            # 2. Initialize Embeddings
            print("  → Loading embeddings provider...")
            self._embeddings = await self._create_embeddings()
            
            # 3. Create ChatService
            print("  → Creating chat service...")
            self._chat_service = ChatService(
                llm=self._llm,
                embeddings=self._embeddings,
            )
            
            # 4. Initialize service (database connections, indexes)
            print("  → Initializing database connections...")
            await self._chat_service.initialize()
            
            self._initialized = True
            print("✅ Chat Service initialized successfully!")
    
    async def _create_llm(self):
        """Create LLM instance based on configuration."""
        from app.llm import get_llm
        from app.llm.config import get_llm_config
        
        config = get_llm_config()
        print(f"    LLM Provider: {config.provider.value}")
        print(f"    Model: {config.model}")
        
        llm = get_llm()
        
        # Health check
        try:
            is_healthy = await llm.health_check()
            if is_healthy:
                print(f"    ✓ LLM health check passed")
            else:
                print(f"    ⚠ LLM health check returned false")
        except Exception as e:
            print(f"    ⚠ LLM health check failed: {e}")
        
        return llm
    
    async def _create_embeddings(self):
        """Create embeddings instance based on configuration."""
        from app.llm import get_embeddings
        from app.llm.config import get_embedding_config
        
        config = get_embedding_config()
        print(f"    Embedding Provider: {config.provider.value}")
        print(f"    Model: {config.model}")
        
        return get_embeddings()
    
    def get_service(self) -> ChatService:
        """
        Get the initialized ChatService.
        
        Raises:
            RuntimeError: If not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "ChatService not initialized. Call await manager.initialize() first."
            )
        return self._chat_service
    
    async def shutdown(self):
        """
        Cleanup resources.
        
        Called during application shutdown.
        """
        if self._chat_service:
            print("🛑 Shutting down Chat Service...")
            await self._chat_service.close()
            self._chat_service = None
        
        # Close LLM connections if needed
        if hasattr(self._llm, 'close'):
            await self._llm.close()
        
        self._initialized = False
        print("✅ Chat Service shutdown complete")
    
    async def health_check(self) -> dict:
        """Check health of all components."""
        status = {
            "initialized": self._initialized,
            "llm": "unknown",
            "embeddings": "unknown",
            "memory_service": "unknown",
        }
        
        if not self._initialized:
            return status
        
        # Check LLM
        try:
            if await self._llm.health_check():
                status["llm"] = "healthy"
            else:
                status["llm"] = "unhealthy"
        except Exception as e:
            status["llm"] = f"error: {str(e)}"
        
        # Embeddings don't typically have health check
        status["embeddings"] = "healthy"
        
        # Memory service (check DB connection)
        try:
            if self._chat_service._memory_service:
                status["memory_service"] = "healthy"
        except Exception as e:
            status["memory_service"] = f"error: {str(e)}"
        
        return status


# Global instance
_manager: Optional[ChatServiceManager] = None


def get_chat_manager() -> ChatServiceManager:
    """Get the global ChatServiceManager instance."""
    global _manager
    if _manager is None:
        _manager = ChatServiceManager()
    return _manager


async def get_chat_service() -> ChatService:
    """
    Dependency for FastAPI to get ChatService.
    
    Usage in endpoints:
        @app.post("/chat")
        async def chat(
            request: ChatRequest,
            chat_service: ChatService = Depends(get_chat_service),
        ):
            return await chat_service.chat(...)
    """
    manager = get_chat_manager()
    if not manager.is_initialized:
        await manager.initialize()
    return manager.get_service()

