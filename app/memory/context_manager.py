"""
Context Manager
===============

Assembles the context window for LLM calls.
Implements the attention-like mechanism for memory retrieval.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from .models import Memory, Entity, Session, WorkingMemory
from .repository import MemoryRepository, EntityRepository, SessionRepository
from .summarization import ContextCompressor


@dataclass
class AssembledContext:
    """The assembled context ready for LLM."""
    system_prompt: str
    character_context: str
    user_context: str
    memory_context: str
    conversation_context: str
    
    # Metadata
    total_tokens: int
    memories_included: int
    messages_included: int
    
    def to_prompt_parts(self) -> List[str]:
        """Return all context parts in order."""
        parts = []
        if self.system_prompt:
            parts.append(self.system_prompt)
        if self.character_context:
            parts.append(f"CHARACTER PROFILE:\n{self.character_context}")
        if self.user_context:
            parts.append(f"ABOUT THE USER:\n{self.user_context}")
        if self.memory_context:
            parts.append(f"RELEVANT MEMORIES:\n{self.memory_context}")
        if self.conversation_context:
            parts.append(f"CONVERSATION:\n{self.conversation_context}")
        return parts
    
    def to_full_prompt(self) -> str:
        """Combine all parts into full prompt."""
        return "\n\n".join(self.to_prompt_parts())


class ContextManager:
    """
    Manages context assembly for character conversations.
    
    Implements attention-like memory retrieval:
    1. Recency - Recent messages always included
    2. Relevance - Semantic search for related memories
    3. Importance - High-importance facts always included
    4. Episodic - Last session summary for continuity
    """
    
    def __init__(
        self,
        memory_repo: MemoryRepository,
        entity_repo: EntityRepository,
        session_repo: SessionRepository,
        embeddings,
        max_context_tokens: int = 8000,
    ):
        """
        Initialize context manager.
        
        Args:
            memory_repo: Memory repository
            entity_repo: Entity repository  
            session_repo: Session repository
            embeddings: Embedding service for semantic search
            max_context_tokens: Max tokens for context window
        """
        self._memory_repo = memory_repo
        self._entity_repo = entity_repo
        self._session_repo = session_repo
        self._embeddings = embeddings
        self._compressor = ContextCompressor(max_context_tokens)
    
    async def assemble_context(
        self,
        user_id: str,
        character_name: str,
        character_profile: str,
        current_message: str,
        session: Session,
    ) -> AssembledContext:
        """
        Assemble full context for LLM call.
        
        This is the main method that brings together all memory types
        and fits them into the context window.
        
        Args:
            user_id: User ID
            character_name: Character being chatted with
            character_profile: Character's profile/description
            current_message: User's current message
            session: Current chat session
            
        Returns:
            AssembledContext ready for LLM
        """
        # 1. System prompt (always included)
        system_prompt = self._build_system_prompt(character_name)
        
        # 2. Character context (always included)
        character_context = character_profile
        
        # 3. User context from entities
        entities = await self._entity_repo.get_user_entities(
            user_id, character_name, limit=10
        )
        user_context = self._format_user_entities(entities)
        
        # 4. Memory context (attention mechanism)
        memory_context, memories_count = await self._retrieve_memories(
            user_id, character_name, current_message, session
        )
        
        # 5. Conversation context (messages)
        message_budget = self._compressor.calculate_message_budget()
        conversation_context, messages_count = self._build_conversation_context(
            session, message_budget
        )
        
        # Estimate total tokens
        total_tokens = sum([
            self._compressor.estimate_tokens(system_prompt),
            self._compressor.estimate_tokens(character_context),
            self._compressor.estimate_tokens(user_context),
            self._compressor.estimate_tokens(memory_context),
            self._compressor.estimate_tokens(conversation_context),
        ])
        
        return AssembledContext(
            system_prompt=system_prompt,
            character_context=character_context,
            user_context=user_context,
            memory_context=memory_context,
            conversation_context=conversation_context,
            total_tokens=total_tokens,
            memories_included=memories_count,
            messages_included=messages_count,
        )
    
    def _build_system_prompt(self, character_name: str) -> str:
        """Build the system prompt."""
        return f"""You are {character_name}. You are having a conversation with a user who wants to interact with you as the character.

IMPORTANT GUIDELINES:
- Stay in character at all times
- Use the memories and context provided to personalize your responses
- Reference past conversations when relevant ("Last time you mentioned...")
- Remember and use the user's name and personal details
- Be emotionally intelligent and responsive to the user's mood
- Keep responses engaging and conversational

You have access to:
- Your character profile and personality
- Information about the user from past conversations
- Relevant memories from your conversations together
- The current conversation history"""

    def _format_user_entities(self, entities: List[Entity]) -> str:
        """Format user entities into context string."""
        if not entities:
            return "No prior information about the user."
        
        lines = ["What I know about the user:"]
        
        # Group by type
        people = [e for e in entities if e.entity_type.value == "person"]
        places = [e for e in entities if e.entity_type.value == "place"]
        things = [e for e in entities if e.entity_type.value in ("thing", "organization")]
        
        if people:
            lines.append("\nPeople in their life:")
            for p in people[:5]:
                detail = f" - {p.details}" if p.details else ""
                lines.append(f"  • {p.name}: {p.relationship or 'mentioned'}{detail}")
        
        if places:
            lines.append("\nPlaces:")
            for p in places[:3]:
                lines.append(f"  • {p.name}: {p.relationship or 'mentioned'}")
        
        if things:
            lines.append("\nOther:")
            for t in things[:3]:
                lines.append(f"  • {t.name}: {t.relationship or 'mentioned'}")
        
        return "\n".join(lines)
    
    async def _retrieve_memories(
        self,
        user_id: str,
        character_name: str,
        current_message: str,
        session: Session,
    ) -> Tuple[str, int]:
        """
        Retrieve relevant memories using attention mechanism.
        
        Combines:
        - Semantically relevant memories (query-based)
        - High-importance memories (always included)
        - Last session summary (episodic)
        - Working memory (if long conversation)
        """
        memory_parts = []
        total_memories = 0
        
        # 1. High-importance memories (always included)
        important = await self._memory_repo.get_important_memories(
            user_id, character_name, min_importance=0.8, limit=3
        )
        if important:
            memory_parts.append("Key facts about this user:")
            for m in important:
                memory_parts.append(f"  • {m.content}")
                total_memories += 1
        
        # 2. Semantically relevant memories
        if current_message:
            query_embedding = self._embeddings.embed_query(current_message)
            relevant = await self._memory_repo.search_memories(
                user_id, character_name, query_embedding,
                limit=4, min_importance=0.3
            )
            
            # Filter out duplicates from important
            important_contents = {m.content for m in important}
            relevant = [(m, s) for m, s in relevant if m.content not in important_contents]
            
            if relevant:
                memory_parts.append("\nRelevant to current conversation:")
                for memory, score in relevant:
                    memory_parts.append(f"  • {memory.content}")
                    total_memories += 1
        
        # 3. Last session summary (episodic memory)
        last_summary = await self._session_repo.get_last_session_summary(
            user_id, character_name
        )
        if last_summary:
            memory_parts.append(f"\nFrom our last conversation: {last_summary}")
            total_memories += 1
        
        # 4. Working memory (if long conversation)
        if session.working_memory and session.message_count > 10:
            if session.working_memory.summary:
                memory_parts.append(
                    f"\nEarlier in this conversation: {session.working_memory.summary}"
                )
        
        return "\n".join(memory_parts), total_memories
    
    def _build_conversation_context(
        self,
        session: Session,
        token_budget: int,
    ) -> Tuple[str, int]:
        """Build conversation context from session messages."""
        if not session.messages:
            return "", 0
        
        # Convert to dict format
        messages = [{"role": m.role, "content": m.content} for m in session.messages]
        
        # Fit to budget
        fitted = self._compressor.fit_messages_to_budget(messages, token_budget)
        
        if not fitted:
            return "", 0
        
        # Format messages
        lines = []
        for msg in fitted:
            role = "User" if msg["role"] == "user" else "Character"
            lines.append(f"{role}: {msg['content']}")
        
        return "\n".join(lines), len(fitted)


class AttentionScorer:
    """
    Calculates attention scores for memories.
    
    Similar to transformer attention, but across memory types:
    - Query: Current user message
    - Keys: Memory contents
    - Values: Memory importance, recency, frequency
    """
    
    @staticmethod
    def calculate_memory_attention(
        memory: Memory,
        semantic_similarity: float,
        current_time: datetime,
    ) -> float:
        """
        Calculate attention score for a memory.
        
        Higher score = more likely to be included in context.
        
        Args:
            memory: The memory to score
            semantic_similarity: Cosine similarity to current query (0-1)
            current_time: Current timestamp
            
        Returns:
            Attention score (0-1)
        """
        # Semantic relevance (40%)
        semantic_score = semantic_similarity * 0.4
        
        # Recency decay with half-life of 7 days (20%)
        if memory.last_accessed:
            days_old = (current_time - memory.last_accessed).days
            recency_score = (0.5 ** (days_old / 7)) * 0.2
        else:
            recency_score = 0.1
        
        # Base importance (30%)
        importance_score = memory.importance * 0.3
        
        # Access frequency bonus (10%)
        frequency_score = min(memory.access_count / 10, 1.0) * 0.1
        
        return semantic_score + recency_score + importance_score + frequency_score
    
    @staticmethod
    def should_include_memory(
        attention_score: float,
        threshold: float = 0.3,
    ) -> bool:
        """Decide if memory should be included based on attention score."""
        return attention_score >= threshold

