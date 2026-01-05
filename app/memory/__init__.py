"""
Memory Module
=============

Sophisticated memory system for character conversations.

Architecture:
- Short-term: Recent messages (sliding window)
- Working: Session summary (compressed context)  
- Long-term: Persistent facts (semantic retrieval)
- Episodic: Past session summaries
- Entity: User's world (people, places, things)
"""

from .models import (
    Memory,
    MemoryType,
    Session,
    Entity,
    EntityType,
    WorkingMemory,
)
from .context_manager import ContextManager
from .service import MemoryService

__all__ = [
    "Memory",
    "MemoryType", 
    "Session",
    "Entity",
    "EntityType",
    "WorkingMemory",
    "ContextManager",
    "MemoryService",
]

