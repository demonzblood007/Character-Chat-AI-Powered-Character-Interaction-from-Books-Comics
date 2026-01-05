"""
Chat Schemas
============

Request and response models for chat endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    character_name: str = Field(..., description="Name of the character to chat with")
    message: str = Field(..., description="User's message", min_length=1, max_length=4000)
    session_id: Optional[str] = Field(None, description="Optional session ID to continue")
    
    class Config:
        json_schema_extra = {
            "example": {
                "character_name": "Batman",
                "message": "Hello, who are you?",
            }
        }


class ChatResponseSchema(BaseModel):
    """Response from chat endpoint."""
    response: str = Field(..., description="Character's response")
    character: str = Field(..., description="Character name")
    timestamp: str = Field(..., description="Response timestamp")
    session_id: str = Field(..., description="Session ID")
    memories_used: int = Field(0, description="Number of memories used in context")
    is_new_session: bool = Field(False, description="Whether this is a new session")
    tokens_used: int = Field(0, description="Total tokens used")
    warning: Optional[str] = Field(None, description="Optional warning message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "I am Batman, the Dark Knight of Gotham.",
                "character": "Batman",
                "timestamp": "2024-01-15T10:30:00Z",
                "session_id": "session123",
                "memories_used": 3,
                "is_new_session": False,
                "tokens_used": 450,
            }
        }


class ConversationSummary(BaseModel):
    """Summary of user's conversation history with a character."""
    total_sessions: int = Field(..., description="Total number of sessions")
    total_messages: int = Field(..., description="Total messages exchanged")
    total_memories: int = Field(..., description="Number of stored memories")
    total_entities: int = Field(..., description="Number of known entities about user")
    last_session_summary: Optional[str] = Field(None, description="Summary of last session")
    active_session: Optional[Dict[str, Any]] = Field(None, description="Current active session info")


class MemoryClearResponse(BaseModel):
    """Response when clearing memories."""
    deleted_count: int = Field(..., description="Number of memories deleted")
    message: str = Field(..., description="Status message")


class ChatMetrics(BaseModel):
    """LLM usage metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens: int
    estimated_cost_usd: float
    error_rate: float

