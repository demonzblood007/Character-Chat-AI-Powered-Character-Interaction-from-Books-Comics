"""
Chat Router
===========

FastAPI router for chat endpoints.
Integrates memory system and LLM providers.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional

from .schemas import (
    ChatRequest,
    ChatResponseSchema,
    ConversationSummary,
    MemoryClearResponse,
    ChatMetrics,
)
from .manager import get_chat_service
from .service import ChatService

# Import auth dependencies
from app.auth import get_current_user_optional
from app.users.models import User


router = APIRouter(prefix="/v2", tags=["Chat v2"])


async def get_user_id_for_chat(
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> str:
    """
    Get user ID from JWT token or X-User-ID header.
    Supports both new JWT auth and legacy header auth.
    """
    if current_user:
        return current_user.id
    if x_user_id:
        return x_user_id
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide JWT token or X-User-ID header."
    )


@router.post(
    "/chat",
    response_model=ChatResponseSchema,
    summary="Chat with a character",
    description="Send a message to a character and receive a response with memory integration.",
)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_user_id_for_chat),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Chat with a character using the new memory-integrated system.
    
    Features:
    - Long-term memory across sessions
    - Automatic fact extraction
    - Context-aware responses
    - RAG from source material
    """
    result = await chat_service.chat(
        user_id=user_id,
        character_name=request.character_name,
        message=request.message,
    )
    
    if result.error:
        if result.error == "CHARACTER_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.response)
        raise HTTPException(status_code=500, detail=result.error)
    
    return ChatResponseSchema(
        response=result.response,
        character=result.character,
        timestamp=result.timestamp,
        session_id=result.session_id,
        memories_used=result.memories_used,
        is_new_session=result.is_new_session,
        tokens_used=result.tokens_used,
    )


@router.post(
    "/chat/stream",
    summary="Streaming chat with a character",
    description="Stream a character's response token by token.",
)
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_user_id_for_chat),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Streaming chat endpoint using Server-Sent Events.
    
    Event types:
    - status: Progress updates
    - start: Generation started
    - chunk: Response token
    - done: Complete with metadata
    - error: Error occurred
    """
    async def generate() -> AsyncGenerator[str, None]:
        async for chunk in chat_service.chat_stream(
            user_id=user_id,
            character_name=request.character_name,
            message=request.message,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get(
    "/chat/summary",
    response_model=ConversationSummary,
    summary="Get conversation summary",
    description="Get a summary of your conversation history with a character.",
)
async def get_conversation_summary(
    character: str = Query(..., description="Character name"),
    user_id: str = Depends(get_user_id_for_chat),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get summary of conversation history with a character."""
    summary = await chat_service.get_conversation_summary(user_id, character)
    return ConversationSummary(**summary)


@router.delete(
    "/chat/memories",
    response_model=MemoryClearResponse,
    summary="Clear memories",
    description="Clear all memories for a character (character forgets everything about you).",
)
async def clear_memories(
    character: str = Query(..., description="Character name"),
    user_id: str = Depends(get_user_id_for_chat),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Clear all memories for a user-character pair."""
    deleted = await chat_service.clear_memories(user_id, character)
    return MemoryClearResponse(
        deleted_count=deleted,
        message=f"Cleared {deleted} memories. {character} has forgotten everything about you.",
    )


@router.get(
    "/chat/metrics",
    response_model=ChatMetrics,
    summary="Get LLM metrics",
    description="Get usage metrics for the LLM service.",
)
async def get_metrics(
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get LLM usage metrics."""
    metrics = await chat_service.get_metrics_summary()
    return ChatMetrics(**metrics)

