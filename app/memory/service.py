"""
Memory Service
==============

Main service that orchestrates all memory operations.
This is the primary interface for the chat system.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import Memory, Entity, Session, Message
from .repository import MemoryRepository, EntityRepository, SessionRepository
from .extraction import MemoryExtractor
from .summarization import SummarizationService
from .context_manager import ContextManager, AssembledContext


# Configuration
WORKING_MEMORY_UPDATE_INTERVAL = int(os.getenv("MEMORY_UPDATE_INTERVAL", 5))
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", 2))


class MemoryService:
    """
    Main memory service for character conversations.
    
    Handles:
    - Session management
    - Context assembly for LLM calls
    - Memory extraction and storage
    - Working memory updates
    - Session summarization
    
    Usage:
        service = MemoryService(db, llm, embeddings)
        
        # Before chat
        session = await service.get_or_create_session(user_id, character)
        context = await service.assemble_context(user_id, character, profile, message, session)
        
        # After chat
        await service.process_message_exchange(session, user_msg, assistant_msg)
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        llm,
        embeddings,
        max_context_tokens: int = 8000,
    ):
        """
        Initialize memory service.
        
        Args:
            db: MongoDB database
            llm: LLM instance for extraction/summarization
            embeddings: Embedding service for semantic search
            max_context_tokens: Max tokens for context window
        """
        # Repositories
        self._memory_repo = MemoryRepository(db)
        self._entity_repo = EntityRepository(db)
        self._session_repo = SessionRepository(db)
        
        # Services
        self._extractor = MemoryExtractor(llm)
        self._summarizer = SummarizationService(llm)
        self._context_manager = ContextManager(
            self._memory_repo,
            self._entity_repo,
            self._session_repo,
            embeddings,
            max_context_tokens,
        )
        
        self._embeddings = embeddings
        self._llm = llm
    
    async def initialize(self):
        """Initialize indexes and collections."""
        await self._memory_repo.ensure_indexes()
        await self._entity_repo.ensure_indexes()
        await self._session_repo.ensure_indexes()
    
    # ─────────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────────
    
    async def get_or_create_session(
        self,
        user_id: str,
        character_name: str,
    ) -> Session:
        """
        Get active session or create new one.
        
        Also handles session timeout - if last message was > SESSION_TIMEOUT_HOURS,
        ends old session and creates new one.
        
        Args:
            user_id: User ID
            character_name: Character name
            
        Returns:
            Active session
        """
        session, is_new = await self._session_repo.get_or_create_session(
            user_id, character_name
        )
        
        if not is_new and session.messages:
            # Check for timeout
            last_message = session.messages[-1]
            if last_message.timestamp:
                hours_since = (datetime.utcnow() - last_message.timestamp).total_seconds() / 3600
                if hours_since > SESSION_TIMEOUT_HOURS:
                    # End old session and create new one
                    await self._end_session(session)
                    session, _ = await self._session_repo.get_or_create_session(
                        user_id, character_name
                    )
        
        return session
    
    async def _end_session(self, session: Session):
        """End a session with final summary."""
        if session.messages:
            messages = [{"role": m.role, "content": m.content} for m in session.messages]
            summary = await self._summarizer.create_session_summary(
                messages,
                session.working_memory.summary if session.working_memory else None,
                session.character_name,
            )
            await self._session_repo.end_session(session.id, summary)
    
    # ─────────────────────────────────────────────────────────────────
    # Context Assembly (Pre-Chat)
    # ─────────────────────────────────────────────────────────────────
    
    async def assemble_context(
        self,
        user_id: str,
        character_name: str,
        character_profile: str,
        current_message: str,
        session: Session,
    ) -> AssembledContext:
        """
        Assemble context for LLM call.
        
        This is called BEFORE generating a response.
        
        Args:
            user_id: User ID
            character_name: Character name
            character_profile: Character's profile/persona
            current_message: User's current message
            session: Current session
            
        Returns:
            AssembledContext ready for LLM
        """
        return await self._context_manager.assemble_context(
            user_id,
            character_name,
            character_profile,
            current_message,
            session,
        )
    
    # ─────────────────────────────────────────────────────────────────
    # Message Processing (Post-Chat)
    # ─────────────────────────────────────────────────────────────────
    
    async def process_message_exchange(
        self,
        session: Session,
        user_message: str,
        assistant_response: str,
        user_tokens: int = 0,
        assistant_tokens: int = 0,
    ) -> Session:
        """
        Process a message exchange after LLM response.
        
        This is called AFTER generating a response.
        
        1. Adds messages to session
        2. Extracts memories and entities
        3. Updates working memory if needed
        
        Args:
            session: Current session
            user_message: User's message
            assistant_response: Character's response
            user_tokens: Token count for user message
            assistant_tokens: Token count for response
            
        Returns:
            Updated session
        """
        # 1. Add messages to session
        await self._session_repo.add_message_to_session(
            session.id, "user", user_message, user_tokens
        )
        await self._session_repo.add_message_to_session(
            session.id, "assistant", assistant_response, assistant_tokens
        )
        
        # Update local session object
        session.add_message("user", user_message, user_tokens)
        session.add_message("assistant", assistant_response, assistant_tokens)
        
        # 2. Extract memories in background (non-blocking)
        # For production, this should be a background task
        await self._extract_and_store_memories(session, user_message)
        
        # 3. Update working memory if needed
        if session.needs_summary_update(WORKING_MEMORY_UPDATE_INTERVAL):
            await self._update_working_memory(session)
        
        return session
    
    async def _extract_and_store_memories(
        self,
        session: Session,
        user_message: str,
    ):
        """Extract and store memories from recent messages."""
        # Only extract from recent messages (last 4 = 2 exchanges)
        recent_messages = [
            {"role": m.role, "content": m.content}
            for m in session.get_recent_messages(4)
        ]
        
        if not recent_messages:
            return
        
        # Extract memories and entities
        memories, entities = await self._extractor.extract_from_messages(
            session.user_id,
            session.character_name,
            recent_messages,
            session.id,
        )
        
        # Store memories with embeddings
        for memory in memories:
            try:
                embedding = self._embeddings.embed_query(memory.content)
                await self._memory_repo.create_memory(memory, embedding)
            except Exception as e:
                print(f"Failed to store memory: {e}")
        
        # Store/update entities
        for entity in entities:
            try:
                await self._entity_repo.upsert_entity(entity)
            except Exception as e:
                print(f"Failed to store entity: {e}")
    
    async def _update_working_memory(self, session: Session):
        """Update session's working memory with summary."""
        # Get messages since last update
        last_update_idx = 0
        if session.working_memory:
            last_update_idx = session.working_memory.last_updated_at_message
        
        new_messages = [
            {"role": m.role, "content": m.content}
            for m in session.messages[last_update_idx:]
        ]
        
        if not new_messages:
            return
        
        # Generate updated summary
        previous_summary = session.working_memory.summary if session.working_memory else None
        result = await self._summarizer.update_working_memory(
            previous_summary,
            new_messages,
            session.character_name,
        )
        
        # Update in database
        await self._session_repo.update_working_memory(
            session.id,
            result["summary"],
            result["key_topics"],
            result["emotional_state"],
            result["unresolved_questions"],
            session.message_count,
        )
    
    # ─────────────────────────────────────────────────────────────────
    # Memory Management
    # ─────────────────────────────────────────────────────────────────
    
    async def get_user_memories(
        self,
        user_id: str,
        character_name: str,
        limit: int = 20,
    ) -> List[Memory]:
        """Get all memories for a user-character pair."""
        return await self._memory_repo.get_recent_memories(
            user_id, character_name, days=365, limit=limit
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        return await self._memory_repo.delete_memory(memory_id)
    
    async def clear_user_memories(
        self,
        user_id: str,
        character_name: str,
    ) -> int:
        """Clear all memories for a user-character pair."""
        memories = await self.get_user_memories(user_id, character_name, limit=1000)
        deleted = 0
        for memory in memories:
            if await self.delete_memory(memory.id):
                deleted += 1
        return deleted
    
    # ─────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────
    
    async def get_conversation_summary(
        self,
        user_id: str,
        character_name: str,
    ) -> Dict[str, Any]:
        """
        Get a summary of the user's conversation history with a character.
        
        Returns:
            Dict with stats and summaries
        """
        # Get past sessions
        past_sessions = await self._session_repo.get_past_sessions(
            user_id, character_name, limit=5
        )
        
        # Get active session
        active_session = await self._session_repo.get_active_session(
            user_id, character_name
        )
        
        # Get memories count
        memories = await self.get_user_memories(user_id, character_name, limit=100)
        
        # Get entities
        entities = await self._entity_repo.get_user_entities(
            user_id, character_name, limit=20
        )
        
        return {
            "total_sessions": len(past_sessions) + (1 if active_session else 0),
            "total_messages": sum(s.message_count for s in past_sessions) + 
                             (active_session.message_count if active_session else 0),
            "total_memories": len(memories),
            "total_entities": len(entities),
            "last_session_summary": past_sessions[0].final_summary if past_sessions else None,
            "active_session": {
                "message_count": active_session.message_count,
                "started_at": active_session.started_at,
            } if active_session else None,
        }

