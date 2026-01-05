"""
Memory Domain Models
====================

Core models for the memory system.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from bson import ObjectId


class MemoryType(str, Enum):
    """Types of long-term memories."""
    FACT = "fact"           # "User's name is Sarah"
    PREFERENCE = "preference"  # "User prefers short answers"
    EMOTION = "emotion"     # "User felt sad about their father"
    EVENT = "event"         # "User mentioned they got promoted"
    OPINION = "opinion"     # "User thinks Batman is too dark"


class EntityType(str, Enum):
    """Types of entities in user's world."""
    PERSON = "person"       # Family, friends, coworkers
    PLACE = "place"         # Cities, locations
    THING = "thing"         # Objects, possessions
    ORGANIZATION = "organization"  # Companies, schools
    EVENT = "event"         # Birthdays, anniversaries


@dataclass
class Memory:
    """
    A single long-term memory about the user.
    
    These are facts, preferences, emotions extracted from conversations
    and stored for future retrieval.
    """
    id: Optional[str] = None
    user_id: str = ""
    character_name: str = ""
    
    # Content
    memory_type: MemoryType = MemoryType.FACT
    content: str = ""
    
    # Importance & relevance
    importance: float = 0.5  # 0-1 scale
    
    # Access tracking (for decay/reinforcement)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Source tracking
    source_session_id: Optional[str] = None
    source_message: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Embedding (stored separately in Qdrant, but ID reference here)
    embedding_id: Optional[str] = None
    
    def __post_init__(self):
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
        if self.last_accessed is None:
            self.last_accessed = now
    
    def record_access(self):
        """Record that this memory was accessed/retrieved."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "character_name": self.character_name,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "source_session_id": self.source_session_id,
            "source_message": self.source_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "embedding_id": self.embedding_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(
            id=str(data["_id"]) if data.get("_id") else None,
            user_id=data.get("user_id", ""),
            character_name=data.get("character_name", ""),
            memory_type=MemoryType(data.get("memory_type", "fact")),
            content=data.get("content", ""),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed"),
            source_session_id=data.get("source_session_id"),
            source_message=data.get("source_message"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            embedding_id=data.get("embedding_id"),
        )


@dataclass 
class Entity:
    """
    An entity in the user's world (person, place, thing).
    
    Tracks people, places, and things the user mentions
    to build understanding of their world.
    """
    id: Optional[str] = None
    user_id: str = ""
    character_name: Optional[str] = None  # None = global entity
    
    # Entity info
    entity_type: EntityType = EntityType.PERSON
    name: str = ""
    relationship: Optional[str] = None  # "user's sister", "user's workplace"
    details: Optional[str] = None
    
    # Tracking
    first_mentioned: Optional[datetime] = None
    last_mentioned: Optional[datetime] = None
    mention_count: int = 1
    
    def __post_init__(self):
        now = datetime.utcnow()
        if self.first_mentioned is None:
            self.first_mentioned = now
        if self.last_mentioned is None:
            self.last_mentioned = now
    
    def record_mention(self):
        """Record another mention of this entity."""
        self.mention_count += 1
        self.last_mentioned = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "character_name": self.character_name,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "relationship": self.relationship,
            "details": self.details,
            "first_mentioned": self.first_mentioned,
            "last_mentioned": self.last_mentioned,
            "mention_count": self.mention_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        return cls(
            id=str(data["_id"]) if data.get("_id") else None,
            user_id=data.get("user_id", ""),
            character_name=data.get("character_name"),
            entity_type=EntityType(data.get("entity_type", "person")),
            name=data.get("name", ""),
            relationship=data.get("relationship"),
            details=data.get("details"),
            first_mentioned=data.get("first_mentioned"),
            last_mentioned=data.get("last_mentioned"),
            mention_count=data.get("mention_count", 1),
        )


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None
    token_count: Optional[int] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "token_count": self.token_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp"),
            token_count=data.get("token_count"),
        )


@dataclass
class WorkingMemory:
    """
    Working memory for a session - compressed summary of conversation.
    Updated periodically to maintain context.
    """
    session_id: str
    summary: str = ""
    key_topics: List[str] = field(default_factory=list)
    user_emotional_state: Optional[str] = None
    unresolved_questions: List[str] = field(default_factory=list)
    last_updated_at_message: int = 0  # Message index when last updated
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "summary": self.summary,
            "key_topics": self.key_topics,
            "user_emotional_state": self.user_emotional_state,
            "unresolved_questions": self.unresolved_questions,
            "last_updated_at_message": self.last_updated_at_message,
            "updated_at": self.updated_at,
        }


@dataclass
class Session:
    """
    A chat session between user and character.
    Contains messages and working memory.
    """
    id: Optional[str] = None
    user_id: str = ""
    character_name: str = ""
    
    # Session state
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    is_active: bool = True
    
    # Messages
    messages: List[Message] = field(default_factory=list)
    message_count: int = 0
    total_tokens: int = 0
    
    # Working memory (current summary)
    working_memory: Optional[WorkingMemory] = None
    
    # Final summary (when session ends)
    final_summary: Optional[str] = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.utcnow()
        if self.working_memory is None and self.id:
            self.working_memory = WorkingMemory(session_id=self.id)
    
    def add_message(self, role: str, content: str, token_count: int = 0):
        """Add a message to the session."""
        msg = Message(role=role, content=content, token_count=token_count)
        self.messages.append(msg)
        self.message_count += 1
        self.total_tokens += token_count
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get the N most recent messages."""
        return self.messages[-count:] if self.messages else []
    
    def needs_summary_update(self, update_interval: int = 5) -> bool:
        """Check if working memory needs to be updated."""
        if not self.working_memory:
            return self.message_count >= update_interval
        messages_since_update = self.message_count - self.working_memory.last_updated_at_message
        return messages_since_update >= update_interval
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "character_name": self.character_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "is_active": self.is_active,
            "messages": [m.to_dict() for m in self.messages],
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "working_memory": self.working_memory.to_dict() if self.working_memory else None,
            "final_summary": self.final_summary,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        working_memory_data = data.get("working_memory")
        working_memory = None
        if working_memory_data:
            working_memory = WorkingMemory(
                session_id=str(data.get("_id", "")),
                summary=working_memory_data.get("summary", ""),
                key_topics=working_memory_data.get("key_topics", []),
                user_emotional_state=working_memory_data.get("user_emotional_state"),
                unresolved_questions=working_memory_data.get("unresolved_questions", []),
                last_updated_at_message=working_memory_data.get("last_updated_at_message", 0),
                updated_at=working_memory_data.get("updated_at"),
            )
        
        session = cls(
            id=str(data["_id"]) if data.get("_id") else None,
            user_id=data.get("user_id", ""),
            character_name=data.get("character_name", ""),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            is_active=data.get("is_active", True),
            messages=messages,
            message_count=data.get("message_count", len(messages)),
            total_tokens=data.get("total_tokens", 0),
            final_summary=data.get("final_summary"),
        )
        session.working_memory = working_memory
        return session

