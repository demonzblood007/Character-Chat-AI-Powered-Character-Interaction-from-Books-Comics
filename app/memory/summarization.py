"""
Summarization Service
=====================

Handles working memory updates and session summarization.
Compresses long conversations into manageable context.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime


class SummarizationService:
    """
    Manages conversation summarization for memory compression.
    
    Two types of summaries:
    1. Working Memory: Updated every N messages, keeps current context
    2. Session Summary: Created at session end for episodic memory
    """
    
    def __init__(self, llm):
        """
        Initialize with LLM.
        
        Args:
            llm: LLM instance with invoke/ainvoke methods
        """
        self._llm = llm
    
    async def update_working_memory(
        self,
        previous_summary: Optional[str],
        new_messages: List[Dict[str, str]],
        character_name: str,
    ) -> Dict[str, any]:
        """
        Update working memory with new messages.
        
        This creates a compressed representation of the conversation
        that can fit in the context window.
        
        Args:
            previous_summary: Previous working memory summary
            new_messages: New messages since last update
            character_name: Character name for context
            
        Returns:
            Dict with summary, key_topics, emotional_state, unresolved_questions
        """
        messages_text = self._format_messages(new_messages)
        
        prompt = f"""You are updating the working memory for a conversation between a user and {character_name}.

Previous Summary:
{previous_summary or "This is the start of the conversation."}

New Messages:
{messages_text}

Create an updated summary that captures:
1. Main topics discussed (as a list)
2. User's current emotional state (one word or phrase)
3. Any unresolved questions the user has (as a list)
4. A brief narrative summary (2-3 sentences)

Return JSON:
{{
  "summary": "Brief narrative of what's been discussed...",
  "key_topics": ["topic1", "topic2"],
  "emotional_state": "curious and engaged",
  "unresolved_questions": ["question1", "question2"]
}}

Return ONLY valid JSON."""

        try:
            response = await self._llm.ainvoke(prompt)
            response = response.strip().strip("```json").strip("```").strip()
            
            result = json.loads(response)
            return {
                "summary": result.get("summary", ""),
                "key_topics": result.get("key_topics", []),
                "emotional_state": result.get("emotional_state"),
                "unresolved_questions": result.get("unresolved_questions", []),
            }
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Working memory update failed: {e}")
            return {
                "summary": previous_summary or "",
                "key_topics": [],
                "emotional_state": None,
                "unresolved_questions": [],
            }
    
    async def create_session_summary(
        self,
        messages: List[Dict[str, str]],
        working_memory: Optional[str],
        character_name: str,
    ) -> str:
        """
        Create final summary when session ends.
        
        This becomes part of episodic memory for future sessions.
        
        Args:
            messages: All messages in the session
            working_memory: Current working memory summary
            character_name: Character name
            
        Returns:
            Session summary string
        """
        # If conversation is short, summarize directly
        if len(messages) <= 10:
            messages_text = self._format_messages(messages)
        else:
            # Use working memory + recent messages for longer conversations
            recent = self._format_messages(messages[-5:])
            messages_text = f"Working Memory: {working_memory}\n\nRecent Messages:\n{recent}"
        
        prompt = f"""Summarize this conversation between a user and {character_name} for future reference.

{messages_text}

Create a brief summary (2-3 sentences) that captures:
- What the user wanted to discuss
- Key emotional moments or revelations
- Any plans, promises, or unfinished topics

This summary will be shown to {character_name} in future conversations as:
"Last time we spoke, [your summary]"

Write the summary from the character's perspective.
Return ONLY the summary text, nothing else."""

        try:
            response = await self._llm.ainvoke(prompt)
            return response.strip()
            
        except Exception as e:
            print(f"Session summary failed: {e}")
            return f"We had a conversation about various topics."
    
    async def compress_messages(
        self,
        messages: List[Dict[str, str]],
        target_token_count: int = 500,
    ) -> str:
        """
        Compress a set of messages into a shorter representation.
        
        Used when messages exceed token budget but need to be included.
        
        Args:
            messages: Messages to compress
            target_token_count: Approximate target length
            
        Returns:
            Compressed representation
        """
        messages_text = self._format_messages(messages)
        
        prompt = f"""Compress this conversation into a brief summary of about {target_token_count // 4} words.
Preserve the key information, topics discussed, and any important details.

Conversation:
{messages_text}

Compressed version:"""

        try:
            response = await self._llm.ainvoke(prompt)
            return response.strip()
            
        except Exception as e:
            print(f"Message compression failed: {e}")
            # Fallback: truncate to recent messages
            recent = messages[-3:] if len(messages) > 3 else messages
            return self._format_messages(recent)
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into readable text."""
        lines = []
        for msg in messages:
            role = "User" if msg.get("role") == "user" else "Character"
            content = msg.get("content", "")[:500]  # Truncate long messages
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


class ContextCompressor:
    """
    Manages token budget and decides what to include in context.
    
    Uses a priority system:
    1. System prompt (always)
    2. Character profile (always)
    3. High-importance memories (always)
    4. Recent messages (sliding window)
    5. Retrieved memories (based on query)
    6. Working memory (if conversation is long)
    7. Episodic memory (last session)
    """
    
    # Approximate token counts for planning
    TOKENS = {
        "system_prompt": 300,
        "character_profile": 500,
        "user_profile": 200,
        "important_memories": 300,
        "retrieved_memories": 400,
        "working_memory": 200,
        "episodic_memory": 150,
        "response_reserve": 1000,
    }
    
    def __init__(self, max_context_tokens: int = 8000):
        """
        Initialize compressor.
        
        Args:
            max_context_tokens: Maximum tokens for context window
        """
        self.max_tokens = max_context_tokens
    
    def calculate_message_budget(self) -> int:
        """Calculate remaining tokens for message buffer."""
        fixed_tokens = sum([
            self.TOKENS["system_prompt"],
            self.TOKENS["character_profile"],
            self.TOKENS["user_profile"],
            self.TOKENS["response_reserve"],
        ])
        
        variable_tokens = sum([
            self.TOKENS["important_memories"],
            self.TOKENS["retrieved_memories"],
            self.TOKENS["working_memory"],
            self.TOKENS["episodic_memory"],
        ])
        
        return self.max_tokens - fixed_tokens - variable_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return len(text) // 4
    
    def fit_messages_to_budget(
        self,
        messages: List[Dict[str, str]],
        budget: int,
    ) -> List[Dict[str, str]]:
        """
        Select messages that fit within token budget.
        
        Prioritizes recent messages (sliding window approach).
        
        Args:
            messages: All messages (oldest first)
            budget: Token budget
            
        Returns:
            Messages that fit in budget (recent first)
        """
        fitted = []
        tokens_used = 0
        
        # Process from most recent
        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            
            if tokens_used + msg_tokens <= budget:
                fitted.insert(0, msg)  # Maintain order
                tokens_used += msg_tokens
            else:
                break
        
        return fitted

