"""
Chat Module
===========

Unified chat service with memory integration and LLM provider abstraction.
"""

from .service import ChatService, ChatResponse
from .manager import ChatServiceManager, get_chat_service

__all__ = [
    "ChatService",
    "ChatResponse",
    "ChatServiceManager",
    "get_chat_service",
]
