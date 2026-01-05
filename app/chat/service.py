"""
Enhanced Chat Service
=====================

Chat service with full memory integration and LLM provider abstraction.
Characters remember users across sessions.

Architecture:
    User Request → ChatService → MemoryService + LLMProvider → Response
                                        ↓
                                  Memory Extraction
                                        ↓
                                  Storage (MongoDB + Qdrant)
"""

import os
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
from dataclasses import dataclass
from neo4j import GraphDatabase
from motor.motor_asyncio import AsyncIOMotorClient

from app.memory.service import MemoryService
from app.memory.context_manager import AssembledContext
from app.llm.providers.base import BaseLLM, BaseEmbeddings, Message, MessageRole, GenerationConfig
from app.llm.monitoring import get_metrics
from app.utils.qdrant_compat import query_points_compat
from app.utils.qdrant_names import qdrant_collection_name_for_vector


# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/character_chat")
MONGODB_DB = os.getenv("MONGODB_DB", "character_chat")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


@dataclass
class ChatResponse:
    """Response from chat service."""
    response: str
    character: str
    timestamp: str
    session_id: str
    memories_used: int = 0
    is_new_session: bool = False
    tokens_used: int = 0
    error: Optional[str] = None


class ChatService:
    """
    Enhanced chat service with persistent memory.
    
    Features:
    - Long-term memory across sessions
    - Automatic fact extraction
    - Context-aware responses
    - Session management
    - Working memory for long conversations
    - Metrics tracking
    
    Usage:
        service = ChatService(llm, embeddings)
        await service.initialize()
        
        response = await service.chat(
            user_id="user123",
            character_name="Batman",
            message="Hello, who are you?"
        )
    """
    
    def __init__(self, llm: BaseLLM, embeddings: BaseEmbeddings):
        """
        Initialize chat service.
        
        Args:
            llm: LLM provider instance (vLLM, Ollama, OpenAI)
            embeddings: Embedding provider instance
        """
        self._llm = llm
        self._embeddings = embeddings
        self._mongo_client = None
        self._memory_service = None
        self._neo4j_driver = None
        self._initialized = False
        self._metrics = get_metrics()
    
    async def initialize(self):
        """Initialize database connections and memory service."""
        if self._initialized:
            return
        
        # MongoDB
        self._mongo_client = AsyncIOMotorClient(MONGODB_URI)
        db = self._mongo_client[MONGODB_DB]
        
        # Memory service
        self._memory_service = MemoryService(
            db=db,
            llm=self._llm,
            embeddings=self._embeddings,
        )
        await self._memory_service.initialize()
        
        # Neo4j
        self._neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        self._initialized = True
    
    async def close(self):
        """Close connections."""
        if self._mongo_client:
            self._mongo_client.close()
        if self._neo4j_driver:
            self._neo4j_driver.close()
        self._initialized = False
    
    async def chat(
        self,
        user_id: str,
        character_name: str,
        message: str,
    ) -> ChatResponse:
        """
        Chat with a character using full memory system.
        
        Pipeline:
        1. Get character profile from Neo4j
        2. Get/create session
        3. Assemble context (memories + history)
        4. Add RAG context from book
        5. Generate response with LLM
        6. Process message (store, extract memories)
        
        Args:
            user_id: User ID
            character_name: Character to chat with
            message: User's message
            
        Returns:
            ChatResponse with response and metadata
        """
        await self.initialize()
        
        timestamp = datetime.utcnow()
        
        # Track metrics
        async with self._metrics.track_request_async(self._llm.model_name) as tracker:
            try:
                # 1. Get character profile from Neo4j
                character_profile = await self._get_character_profile(
                    character_name, user_id
                )
                if not character_profile:
                    return ChatResponse(
                        response=f"Character '{character_name}' not found.",
                        character=character_name,
                        timestamp=timestamp.isoformat(),
                        session_id="",
                        error="CHARACTER_NOT_FOUND"
                    )
                
                # 2. Get or create session
                session = await self._memory_service.get_or_create_session(
                    user_id, character_name
                )
                is_new_session = session.message_count == 0
                
                # 3. Assemble context with memories
                context = await self._memory_service.assemble_context(
                    user_id=user_id,
                    character_name=character_name,
                    character_profile=character_profile["profile_text"],
                    current_message=message,
                    session=session,
                )
                
                # 4. Add RAG context from book
                rag_context = await self._get_rag_context(
                    message, character_profile.get("file_id"), user_id
                )
                
                # 5. Build messages for LLM
                messages = self._build_messages(
                    character_name=character_name,
                    context=context,
                    rag_context=rag_context,
                    current_message=message,
                )
                
                # 6. Generate response
                config = GenerationConfig(
                    temperature=0.8,  # Creative for roleplay
                    max_tokens=1024,
                    top_p=0.9,
                )
                
                result = await self._llm.chat(messages, config)
                response_text = result.text
                
                # Track tokens
                tracker.set_tokens(
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens
                )
                
                # 7. Process message exchange (store messages, extract memories)
                session = await self._memory_service.process_message_exchange(
                    session=session,
                    user_message=message,
                    assistant_response=response_text,
                    user_tokens=self._llm.count_tokens(message),
                    assistant_tokens=result.completion_tokens,
                )
                
                return ChatResponse(
                    response=response_text,
                    character=character_name,
                    timestamp=timestamp.isoformat(),
                    session_id=session.id,
                    memories_used=context.memories_included,
                    is_new_session=is_new_session,
                    tokens_used=result.total_tokens,
                )
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return ChatResponse(
                    response="I apologize, but I'm having trouble responding. Please try again.",
                    character=character_name,
                    timestamp=datetime.utcnow().isoformat(),
                    session_id="",
                    error=str(e),
                )
    
    async def chat_stream(
        self,
        user_id: str,
        character_name: str,
        message: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming chat with memory integration.
        
        Yields status updates and response chunks.
        Uses SSE (Server-Sent Events) format.
        """
        await self.initialize()
        
        try:
            timestamp = datetime.utcnow()
            
            # Status: Starting
            yield {"type": "status", "message": "Connecting..."}
            
            # 1. Get character profile
            yield {"type": "status", "message": f"Loading {character_name}'s profile..."}
            character_profile = await self._get_character_profile(
                character_name, user_id
            )
            if not character_profile:
                yield {"type": "error", "message": f"Character '{character_name}' not found."}
                return
            
            # 2. Get session
            yield {"type": "status", "message": "Loading conversation history..."}
            session = await self._memory_service.get_or_create_session(
                user_id, character_name
            )
            
            # 3. Assemble context
            yield {"type": "status", "message": "Recalling our past conversations..."}
            context = await self._memory_service.assemble_context(
                user_id=user_id,
                character_name=character_name,
                character_profile=character_profile["profile_text"],
                current_message=message,
                session=session,
            )
            
            # 4. RAG context
            yield {"type": "status", "message": "Searching story context..."}
            rag_context = await self._get_rag_context(
                message, character_profile.get("file_id"), user_id
            )
            
            # 5. Build messages
            messages = self._build_messages(
                character_name=character_name,
                context=context,
                rag_context=rag_context,
                current_message=message,
            )
            
            # 6. Generate streaming response
            yield {"type": "status", "message": f"{character_name} is thinking..."}
            yield {"type": "start", "character": character_name}
            
            config = GenerationConfig(
                temperature=0.8,
                max_tokens=1024,
                top_p=0.9,
            )
            
            # Collect full response for storage
            full_response = []
            
            async with self._metrics.track_request_async(self._llm.model_name) as tracker:
                tracker.record_first_token()
                
                async for chunk in self._llm.chat_stream(messages, config):
                    full_response.append(chunk)
                    yield {"type": "chunk", "content": chunk}
            
            response_text = "".join(full_response)
            
            # 7. Process message exchange
            session = await self._memory_service.process_message_exchange(
                session=session,
                user_message=message,
                assistant_response=response_text,
            )
            
            yield {
                "type": "done",
                "character": character_name,
                "timestamp": timestamp.isoformat(),
                "session_id": session.id,
                "memories_used": context.memories_included,
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {"type": "error", "message": str(e)}
    
    def _build_messages(
        self,
        character_name: str,
        context: AssembledContext,
        rag_context: str,
        current_message: str,
    ) -> List[Message]:
        """Build messages for LLM call."""
        messages = []
        
        # System prompt with character persona
        system_content = context.system_prompt
        
        # Add character profile
        system_content += f"\n\n=== CHARACTER PROFILE ===\n{context.character_context}"
        
        # Add user knowledge
        if context.user_context:
            system_content += f"\n\n=== WHAT YOU KNOW ABOUT THE USER ===\n{context.user_context}"
        
        # Add retrieved memories
        if context.memory_context:
            system_content += f"\n\n=== MEMORIES FROM PAST CONVERSATIONS ===\n{context.memory_context}"
        
        # Add RAG context
        if rag_context:
            system_content += f"\n\n=== RELEVANT STORY CONTEXT ===\n{rag_context}"
        
        messages.append(Message(role=MessageRole.SYSTEM, content=system_content))
        
        # Add conversation history
        if context.conversation_context:
            # Parse conversation history and add as messages
            for line in context.conversation_context.split("\n"):
                if line.startswith("User:"):
                    messages.append(Message(
                        role=MessageRole.USER, 
                        content=line[5:].strip()
                    ))
                elif line.startswith(f"{character_name}:") or line.startswith("Assistant:"):
                    prefix_len = len(character_name) + 1 if line.startswith(f"{character_name}:") else 10
                    messages.append(Message(
                        role=MessageRole.ASSISTANT, 
                        content=line[prefix_len:].strip()
                    ))
        
        # Add current message
        messages.append(Message(role=MessageRole.USER, content=current_message))
        
        return messages
    
    async def _get_character_profile(
        self,
        character_name: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get character profile from Neo4j."""
        try:
            with self._neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (c:Character {name: $name, user_id: $user_id})
                    RETURN c.description as description,
                           c.powers as powers,
                           c.story_arcs as story_arcs,
                           c.file_id as file_id,
                           c.aliases as aliases
                """, name=character_name, user_id=user_id)
                
                record = result.single()
                if not record:
                    return None
                
                # Build profile text
                profile_parts = [f"Character: {character_name}"]
                
                if record.get("description"):
                    profile_parts.append(f"Description: {record['description']}")
                
                if record.get("powers"):
                    powers = record['powers']
                    if powers:
                        profile_parts.append(f"Powers/Abilities: {', '.join(powers)}")
                
                if record.get("story_arcs"):
                    arcs = record['story_arcs']
                    if arcs:
                        profile_parts.append(f"Story Arcs: {', '.join(arcs)}")
                
                if record.get("aliases"):
                    aliases = record['aliases']
                    if aliases:
                        profile_parts.append(f"Also known as: {', '.join(aliases)}")
                
                # Add personality note
                personality = self._get_personality_note(character_name)
                if personality:
                    profile_parts.append(f"\nSpeaking Style:\n{personality}")
                
                return {
                    "profile_text": "\n".join(profile_parts),
                    "file_id": record.get("file_id"),
                    "description": record.get("description"),
                    "powers": record.get("powers"),
                }
                
        except Exception as e:
            print(f"Error getting character profile: {e}")
            return None
    
    async def _get_rag_context(
        self,
        query: str,
        file_id: Optional[str],
        user_id: str,
    ) -> str:
        """Get RAG context from Qdrant."""
        if not file_id:
            return ""
        
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            qdrant_host = os.getenv("QDRANT_HOST", "localhost")
            qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
            
            client = QdrantClient(host=qdrant_host, port=qdrant_port)
            
            # Embed query
            query_vector = self._embeddings.embed_query(query)
            
            q_filter = Filter(must=[
                FieldCondition(key="file_id", match=MatchValue(value=file_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            ])

            points = query_points_compat(
                client,
                collection_name=qdrant_collection_name_for_vector(
                    os.getenv("QDRANT_CHUNKS_COLLECTION", "comic_chunks"),
                    query_vector,
                ),
                query_vector=query_vector,
                limit=4,
                query_filter=q_filter,
                with_payload=True,
            )

            texts = []
            for p in points:
                payload = getattr(p, "payload", None) or {}
                text = payload.get("text", "")
                if text:
                    texts.append(text)
            return "\n".join(texts)
            
        except Exception as e:
            print(f"RAG retrieval failed: {e}")
            return ""
    
    def _get_personality_note(self, character_name: str) -> str:
        """Get personality/speaking style notes for known characters."""
        personalities = {
            "batman": "Terse, brooding, intense. Short sentences. Mentions darkness, shadows. Controlled anger. Never jokes.",
            "joker": "Chaotic, theatrical. Laughs mid-sentence. Dark jokes and puns. Unpredictable mood swings.",
            "superman": "Optimistic, earnest, inspirational. References hope and justice. Humble. Speaks with conviction.",
            "spider-man": "Quippy, sarcastic. Pop culture references. Self-deprecating humor. Young and energetic.",
            "hermione": "Intelligent, precise. Often explains thoroughly. References books and rules. Can be bossy.",
            "sherlock holmes": "Analytical, deductive. Points out details others miss. Can be condescending. Bored easily.",
            "harry potter": "Brave, loyal. Sometimes impulsive. Mentions his friends often. Humble about his fame.",
            "gandalf": "Wise, mysterious. Speaks in riddles sometimes. Patient but can be stern. Encouraging.",
            "darth vader": "Commanding, menacing. Short sentences. References the Dark Side. Heavy breathing.",
        }
        
        # Check for exact or partial match
        name_lower = character_name.lower()
        for known, personality in personalities.items():
            if known in name_lower or name_lower in known:
                return personality
        
        return ""
    
    # ─────────────────────────────────────────────────────────────────
    # Memory Management Endpoints
    # ─────────────────────────────────────────────────────────────────
    
    async def get_conversation_summary(
        self,
        user_id: str,
        character_name: str,
    ) -> Dict[str, Any]:
        """Get summary of conversation history."""
        await self.initialize()
        return await self._memory_service.get_conversation_summary(
            user_id, character_name
        )
    
    async def clear_memories(
        self,
        user_id: str,
        character_name: str,
    ) -> int:
        """Clear all memories for a user-character pair."""
        await self.initialize()
        return await self._memory_service.clear_user_memories(
            user_id, character_name
        )
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get LLM usage metrics."""
        summary = self._metrics.get_summary(last_minutes=60)
        return {
            "total_requests": summary.total_requests,
            "successful_requests": summary.successful_requests,
            "failed_requests": summary.failed_requests,
            "avg_latency_ms": round(summary.avg_latency_ms, 2),
            "p95_latency_ms": round(summary.p95_latency_ms, 2),
            "total_tokens": summary.total_prompt_tokens + summary.total_completion_tokens,
            "estimated_cost_usd": round(summary.estimated_cost_usd, 4),
            "error_rate": round(summary.error_rate * 100, 2),
        }
