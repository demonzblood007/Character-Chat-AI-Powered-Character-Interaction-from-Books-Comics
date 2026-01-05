"""
Memory Repository
=================

Data access layer for memory operations.
Handles MongoDB and Qdrant (vector) storage.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, 
    Filter, FieldCondition, MatchValue,
    SearchRequest, ScoredPoint
)

from .models import Memory, MemoryType, Entity, EntityType, Session
from app.utils.qdrant_compat import query_points_compat
from app.utils.qdrant_names import qdrant_collection_name_for_dim


# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
MEMORY_COLLECTION_BASE = os.getenv("QDRANT_MEMORY_COLLECTION", "character_memories")
DEFAULT_VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "1536"))


class MemoryRepository:
    """
    Repository for long-term memory storage and retrieval.
    Uses MongoDB for structured data and Qdrant for semantic search.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._memories: AsyncIOMotorCollection = db["memories"]
        self._qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # We'll ensure collections lazily based on the *actual vector dimension* being used.
        # This prevents "expected dim X got Y" errors if the embedding model changes.
        self._ensure_qdrant_collection(DEFAULT_VECTOR_SIZE)
    
    def _ensure_qdrant_collection(self, dim: int) -> str:
        """Ensure the dimension-suffixed Qdrant collection exists and return its name."""
        collection_name = qdrant_collection_name_for_dim(MEMORY_COLLECTION_BASE, dim)
        collections = [c.name for c in self._qdrant.get_collections().collections]
        if collection_name not in collections:
            self._qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=int(dim), distance=Distance.COSINE)
            )
        return collection_name
    
    async def ensure_indexes(self):
        """Create MongoDB indexes."""
        await self._memories.create_index([("user_id", 1), ("character_name", 1)])
        await self._memories.create_index("importance", background=True)
        await self._memories.create_index("last_accessed", background=True)
    
    # ─────────────────────────────────────────────────────────────────
    # Memory CRUD
    # ─────────────────────────────────────────────────────────────────
    
    async def create_memory(self, memory: Memory, embedding: List[float]) -> Memory:
        """
        Create a new memory with its embedding.
        
        Args:
            memory: Memory to create
            embedding: Vector embedding of memory content
            
        Returns:
            Created memory with ID
        """
        # Store in MongoDB
        doc = memory.to_dict()
        result = await self._memories.insert_one(doc)
        memory.id = str(result.inserted_id)
        
        # Store embedding in Qdrant
        collection_name = self._ensure_qdrant_collection(len(embedding))
        point_id = str(uuid.uuid4())
        self._qdrant.upsert(
            collection_name=collection_name,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "memory_id": memory.id,
                    "user_id": memory.user_id,
                    "character_name": memory.character_name,
                    "memory_type": memory.memory_type.value,
                    "importance": memory.importance,
                    "content": memory.content,
                }
            )]
        )
        
        # Update memory with embedding ID
        memory.embedding_id = point_id
        await self._memories.update_one(
            {"_id": result.inserted_id},
            {"$set": {"embedding_id": point_id}}
        )
        
        return memory
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """Get memory by ID."""
        doc = await self._memories.find_one({"_id": ObjectId(memory_id)})
        return Memory.from_dict(doc) if doc else None
    
    async def update_memory_access(self, memory_id: str) -> None:
        """Record memory access (for relevance tracking)."""
        await self._memories.update_one(
            {"_id": ObjectId(memory_id)},
            {
                "$inc": {"access_count": 1},
                "$set": {"last_accessed": datetime.utcnow()}
            }
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory and its embedding."""
        memory = await self.get_memory_by_id(memory_id)
        if not memory:
            return False
        
        # Delete from Qdrant
        if memory.embedding_id:
            # Best-effort delete across any dimension-suffixed collections (embedding dim may vary over time).
            try:
                cols = [c.name for c in self._qdrant.get_collections().collections]
                for c in cols:
                    if c == MEMORY_COLLECTION_BASE or c.startswith(f"{MEMORY_COLLECTION_BASE}_d"):
                        self._qdrant.delete(collection_name=c, points_selector=[memory.embedding_id])
            except Exception:
                pass
        
        # Delete from MongoDB
        result = await self._memories.delete_one({"_id": ObjectId(memory_id)})
        return result.deleted_count > 0
    
    # ─────────────────────────────────────────────────────────────────
    # Semantic Search
    # ─────────────────────────────────────────────────────────────────
    
    async def search_memories(
        self,
        user_id: str,
        character_name: str,
        query_embedding: List[float],
        limit: int = 5,
        min_importance: float = 0.0,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> List[Tuple[Memory, float]]:
        """
        Search memories by semantic similarity.
        
        Args:
            user_id: User ID
            character_name: Character name
            query_embedding: Query vector
            limit: Max results
            min_importance: Minimum importance threshold
            memory_types: Filter by memory types
            
        Returns:
            List of (Memory, score) tuples sorted by relevance
        """
        # Build filter
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="character_name", match=MatchValue(value=character_name)),
        ]
        
        q_filter = Filter(must=must_conditions)

        collection_name = self._ensure_qdrant_collection(len(query_embedding))
        points = query_points_compat(
            self._qdrant,
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit * 2,
            query_filter=q_filter,
            with_payload=True,
        )
        
        # Fetch full memories from MongoDB and filter
        memories_with_scores = []
        for result in points:
            payload = getattr(result, "payload", None) or {}
            memory_id = payload.get("memory_id")
            if memory_id:
                memory = await self.get_memory_by_id(memory_id)
                if memory and memory.importance >= min_importance:
                    if memory_types is None or memory.memory_type in memory_types:
                        # Record access
                        await self.update_memory_access(memory_id)
                        score = getattr(result, "score", 0.0) or 0.0
                        memories_with_scores.append((memory, score))
        
        return memories_with_scores[:limit]
    
    async def get_important_memories(
        self,
        user_id: str,
        character_name: str,
        min_importance: float = 0.7,
        limit: int = 10,
    ) -> List[Memory]:
        """
        Get high-importance memories (always-include facts).
        
        These are facts that should always be in context regardless of query.
        """
        cursor = self._memories.find({
            "user_id": user_id,
            "character_name": character_name,
            "importance": {"$gte": min_importance}
        }).sort("importance", -1).limit(limit)
        
        memories = []
        async for doc in cursor:
            memories.append(Memory.from_dict(doc))
        return memories
    
    async def get_recent_memories(
        self,
        user_id: str,
        character_name: str,
        days: int = 7,
        limit: int = 10,
    ) -> List[Memory]:
        """Get recently accessed memories."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        cursor = self._memories.find({
            "user_id": user_id,
            "character_name": character_name,
            "last_accessed": {"$gte": cutoff}
        }).sort("last_accessed", -1).limit(limit)
        
        memories = []
        async for doc in cursor:
            memories.append(Memory.from_dict(doc))
        return memories


class EntityRepository:
    """Repository for entity (user's world) storage."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._entities: AsyncIOMotorCollection = db["entities"]
    
    async def ensure_indexes(self):
        """Create MongoDB indexes."""
        await self._entities.create_index([
            ("user_id", 1), 
            ("character_name", 1), 
            ("name", 1)
        ], unique=True)
    
    async def upsert_entity(self, entity: Entity) -> Entity:
        """Create or update an entity."""
        result = await self._entities.find_one_and_update(
            {
                "user_id": entity.user_id,
                "character_name": entity.character_name,
                "name": entity.name,
            },
            {
                "$set": {
                    "entity_type": entity.entity_type.value,
                    "relationship": entity.relationship,
                    "details": entity.details,
                    "last_mentioned": datetime.utcnow(),
                },
                "$inc": {"mention_count": 1},
                "$setOnInsert": {
                    "first_mentioned": datetime.utcnow(),
                }
            },
            upsert=True,
            return_document=True
        )
        return Entity.from_dict(result)
    
    async def get_user_entities(
        self,
        user_id: str,
        character_name: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        limit: int = 20,
    ) -> List[Entity]:
        """Get entities for a user."""
        query = {"user_id": user_id}
        
        # Include both character-specific and global entities
        if character_name:
            query["$or"] = [
                {"character_name": character_name},
                {"character_name": None}
            ]
        
        if entity_type:
            query["entity_type"] = entity_type.value
        
        cursor = self._entities.find(query).sort("mention_count", -1).limit(limit)
        
        entities = []
        async for doc in cursor:
            entities.append(Entity.from_dict(doc))
        return entities


class SessionRepository:
    """Repository for chat sessions."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._sessions: AsyncIOMotorCollection = db["chat_sessions"]
    
    async def ensure_indexes(self):
        """Create MongoDB indexes."""
        await self._sessions.create_index([("user_id", 1), ("character_name", 1)])
        await self._sessions.create_index("started_at", background=True)
        await self._sessions.create_index("is_active", background=True)
    
    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        doc = session.to_dict()
        result = await self._sessions.insert_one(doc)
        session.id = str(result.inserted_id)
        return session
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        doc = await self._sessions.find_one({"_id": ObjectId(session_id)})
        return Session.from_dict(doc) if doc else None
    
    async def get_active_session(
        self,
        user_id: str,
        character_name: str,
    ) -> Optional[Session]:
        """Get active session for user-character pair."""
        doc = await self._sessions.find_one({
            "user_id": user_id,
            "character_name": character_name,
            "is_active": True,
        })
        return Session.from_dict(doc) if doc else None
    
    async def get_or_create_session(
        self,
        user_id: str,
        character_name: str,
    ) -> Tuple[Session, bool]:
        """Get active session or create new one."""
        session = await self.get_active_session(user_id, character_name)
        if session:
            return session, False
        
        new_session = Session(user_id=user_id, character_name=character_name)
        created = await self.create_session(new_session)
        return created, True
    
    async def update_session(self, session: Session) -> Session:
        """Update session data."""
        await self._sessions.update_one(
            {"_id": ObjectId(session.id)},
            {"$set": session.to_dict()}
        )
        return session
    
    async def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
        token_count: int = 0,
    ) -> None:
        """Add a message to session."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "token_count": token_count,
        }
        
        await self._sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"messages": message},
                "$inc": {
                    "message_count": 1,
                    "total_tokens": token_count,
                }
            }
        )
    
    async def update_working_memory(
        self,
        session_id: str,
        summary: str,
        key_topics: List[str],
        emotional_state: Optional[str],
        unresolved_questions: List[str],
        message_index: int,
    ) -> None:
        """Update session's working memory."""
        await self._sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                "working_memory": {
                    "session_id": session_id,
                    "summary": summary,
                    "key_topics": key_topics,
                    "user_emotional_state": emotional_state,
                    "unresolved_questions": unresolved_questions,
                    "last_updated_at_message": message_index,
                    "updated_at": datetime.utcnow(),
                }
            }}
        )
    
    async def end_session(
        self,
        session_id: str,
        final_summary: str,
    ) -> None:
        """End a session with final summary."""
        await self._sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                "is_active": False,
                "ended_at": datetime.utcnow(),
                "final_summary": final_summary,
            }}
        )
    
    async def get_past_sessions(
        self,
        user_id: str,
        character_name: str,
        limit: int = 5,
    ) -> List[Session]:
        """Get past (ended) sessions for user-character pair."""
        cursor = self._sessions.find({
            "user_id": user_id,
            "character_name": character_name,
            "is_active": False,
            "final_summary": {"$ne": None},
        }).sort("ended_at", -1).limit(limit)
        
        sessions = []
        async for doc in cursor:
            sessions.append(Session.from_dict(doc))
        return sessions
    
    async def get_last_session_summary(
        self,
        user_id: str,
        character_name: str,
    ) -> Optional[str]:
        """Get the summary from the most recent past session."""
        doc = await self._sessions.find_one(
            {
                "user_id": user_id,
                "character_name": character_name,
                "is_active": False,
                "final_summary": {"$ne": None},
            },
            sort=[("ended_at", -1)],
            projection={"final_summary": 1}
        )
        return doc.get("final_summary") if doc else None

