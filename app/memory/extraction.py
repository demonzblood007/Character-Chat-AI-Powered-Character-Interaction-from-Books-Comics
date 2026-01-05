"""
Memory Extraction Service
=========================

Extracts important facts, entities, and memories from conversations.
Runs after each message exchange to populate long-term memory.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .models import Memory, MemoryType, Entity, EntityType


class MemoryExtractor:
    """
    Extracts memories and entities from conversation messages.
    
    Uses LLM to identify:
    - User facts (name, job, location, etc.)
    - Preferences and opinions
    - Emotional moments
    - Entities (people, places, things in user's world)
    """
    
    def __init__(self, llm):
        """
        Initialize extractor with LLM.
        
        Args:
            llm: LLM instance with invoke/ainvoke methods
        """
        self._llm = llm
    
    async def extract_from_messages(
        self,
        user_id: str,
        character_name: str,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
    ) -> Tuple[List[Memory], List[Entity]]:
        """
        Extract memories and entities from messages.
        
        Args:
            user_id: User ID
            character_name: Character name
            messages: Recent messages to analyze
            session_id: Optional session ID for source tracking
            
        Returns:
            Tuple of (memories, entities)
        """
        if not messages:
            return [], []
        
        # Format messages for analysis
        conversation_text = self._format_messages(messages)
        
        # Run extraction in parallel
        memories_task = self._extract_memories(
            conversation_text, user_id, character_name, session_id
        )
        entities_task = self._extract_entities(
            conversation_text, user_id, character_name
        )
        
        memories, entities = await asyncio.gather(memories_task, entities_task)
        
        return memories, entities
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into readable text."""
        lines = []
        for msg in messages:
            role = "User" if msg.get("role") == "user" else "Character"
            lines.append(f"{role}: {msg.get('content', '')}")
        return "\n".join(lines)
    
    async def _extract_memories(
        self,
        conversation: str,
        user_id: str,
        character_name: str,
        session_id: Optional[str],
    ) -> List[Memory]:
        """Extract factual memories from conversation."""
        prompt = f"""Analyze this conversation and extract important facts about the USER (not the character).

Conversation:
{conversation}

Extract facts in these categories:
1. FACT: Personal information (name, age, job, location, family)
2. PREFERENCE: Likes, dislikes, opinions, preferences
3. EMOTION: Emotional states, feelings shared, personal struggles
4. EVENT: Events they mentioned (got promoted, going on vacation, etc.)
5. OPINION: Their opinions about topics discussed

For each fact, rate its importance (0.0-1.0):
- 0.9-1.0: Critical identity facts (name, core relationships)
- 0.7-0.8: Important preferences and recurring themes
- 0.5-0.6: Interesting but not essential
- 0.3-0.4: Minor details

Return JSON array:
[
  {{"type": "fact", "content": "User's name is Sarah", "importance": 0.95}},
  {{"type": "preference", "content": "User prefers detailed explanations", "importance": 0.6}},
  {{"type": "emotion", "content": "User expressed feeling lonely lately", "importance": 0.8}}
]

If no clear facts about the user, return empty array [].
Return ONLY valid JSON, no other text."""

        try:
            response = await self._llm.ainvoke(prompt)
            response = response.strip().strip("```json").strip("```").strip()
            
            facts = json.loads(response)
            
            memories = []
            for fact in facts:
                if isinstance(fact, dict) and fact.get("content"):
                    memory = Memory(
                        user_id=user_id,
                        character_name=character_name,
                        memory_type=self._parse_memory_type(fact.get("type", "fact")),
                        content=fact["content"],
                        importance=float(fact.get("importance", 0.5)),
                        source_session_id=session_id,
                    )
                    memories.append(memory)
            
            return memories
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Memory extraction failed: {e}")
            return []
    
    async def _extract_entities(
        self,
        conversation: str,
        user_id: str,
        character_name: str,
    ) -> List[Entity]:
        """Extract entities (people, places, things) from conversation."""
        prompt = f"""Analyze this conversation and extract entities the USER mentioned from their life.

Conversation:
{conversation}

Extract entities in these categories:
1. PERSON: People in user's life (family, friends, coworkers)
2. PLACE: Locations they mentioned (cities, workplaces, etc.)
3. ORGANIZATION: Companies, schools, groups they're part of
4. THING: Important objects or possessions

For each entity, identify the relationship to the user.

Return JSON array:
[
  {{"type": "person", "name": "Sarah", "relationship": "user's sister", "details": "lives in Boston"}},
  {{"type": "place", "name": "TechCorp", "relationship": "user's workplace", "details": "software company"}},
  {{"type": "person", "name": "Max", "relationship": "user's dog", "details": "golden retriever"}}
]

If no clear entities mentioned, return empty array [].
Return ONLY valid JSON, no other text."""

        try:
            response = await self._llm.ainvoke(prompt)
            response = response.strip().strip("```json").strip("```").strip()
            
            entities_data = json.loads(response)
            
            entities = []
            for data in entities_data:
                if isinstance(data, dict) and data.get("name"):
                    entity = Entity(
                        user_id=user_id,
                        character_name=character_name,
                        entity_type=self._parse_entity_type(data.get("type", "thing")),
                        name=data["name"],
                        relationship=data.get("relationship"),
                        details=data.get("details"),
                    )
                    entities.append(entity)
            
            return entities
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Entity extraction failed: {e}")
            return []
    
    def _parse_memory_type(self, type_str: str) -> MemoryType:
        """Parse memory type string to enum."""
        type_map = {
            "fact": MemoryType.FACT,
            "preference": MemoryType.PREFERENCE,
            "emotion": MemoryType.EMOTION,
            "event": MemoryType.EVENT,
            "opinion": MemoryType.OPINION,
        }
        return type_map.get(type_str.lower(), MemoryType.FACT)
    
    def _parse_entity_type(self, type_str: str) -> EntityType:
        """Parse entity type string to enum."""
        type_map = {
            "person": EntityType.PERSON,
            "place": EntityType.PLACE,
            "thing": EntityType.THING,
            "organization": EntityType.ORGANIZATION,
            "event": EntityType.EVENT,
        }
        return type_map.get(type_str.lower(), EntityType.THING)


class ImportanceScorer:
    """
    Scores the importance of memories for retention decisions.
    Uses multiple signals to determine what's worth remembering.
    """
    
    @staticmethod
    def calculate_retention_score(
        memory: Memory,
        current_time: datetime,
    ) -> float:
        """
        Calculate overall retention score for a memory.
        
        Higher scores = more important to keep.
        Used for memory consolidation and cleanup.
        """
        # Base importance
        score = memory.importance * 0.4
        
        # Recency (half-life of 30 days)
        if memory.last_accessed:
            days_old = (current_time - memory.last_accessed).days
            recency_score = 0.5 ** (days_old / 30)
            score += recency_score * 0.2
        
        # Access frequency (normalized)
        frequency_score = min(memory.access_count / 20, 1.0)
        score += frequency_score * 0.2
        
        # Type bonuses
        type_bonuses = {
            MemoryType.FACT: 0.15,      # Identity facts are important
            MemoryType.EMOTION: 0.1,    # Emotional moments matter
            MemoryType.PREFERENCE: 0.05,
            MemoryType.EVENT: 0.05,
            MemoryType.OPINION: 0.05,
        }
        score += type_bonuses.get(memory.memory_type, 0)
        
        return min(score, 1.0)

