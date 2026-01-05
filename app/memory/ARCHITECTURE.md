# Character Memory System Architecture

## Overview

A sophisticated memory system that maintains conversation context across sessions, similar to how ChatGPT/Claude manages long conversations. The system uses a multi-tiered approach combining recency, relevance, and importance.

## Memory Tiers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MEMORY ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CONTEXT WINDOW (sent to LLM)                      │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐   │   │
│  │  │ Character │ │ Retrieved │ │  Working  │ │   Short-term      │   │   │
│  │  │  Profile  │ │ Memories  │ │  Memory   │ │   Buffer          │   │   │
│  │  │           │ │           │ │ (Summary) │ │   (Last N msgs)   │   │   │
│  │  │ ~500 tok  │ │ ~500 tok  │ │ ~300 tok  │ │   ~2000 tokens    │   │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      ▲                                      │
│                                      │ Retrieval                            │
│  ┌───────────────────────────────────┴─────────────────────────────────┐   │
│  │                        MEMORY STORES                                 │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │  LONG-TERM      │  │   EPISODIC      │  │    ENTITY           │  │   │
│  │  │  MEMORY         │  │   MEMORY        │  │    MEMORY           │  │   │
│  │  │                 │  │                 │  │                     │  │   │
│  │  │ • User facts    │  │ • Past session  │  │ • User profile      │  │   │
│  │  │ • Preferences   │  │   summaries     │  │ • Mentioned people  │  │   │
│  │  │ • Key moments   │  │ • "Last time    │  │ • Places, things    │  │   │
│  │  │ • Emotions      │  │   we talked..." │  │ • Relationships     │  │   │
│  │  │                 │  │                 │  │                     │  │   │
│  │  │ [Vector + KV]   │  │ [MongoDB]       │  │ [MongoDB]           │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Memory Types

### 1. Short-term Buffer (Conversation History)
- **What:** Last N messages in current session
- **Storage:** In-memory during session, MongoDB for persistence
- **Window:** Sliding window of ~10-15 messages
- **Purpose:** Immediate conversation context

### 2. Working Memory (Session Summary)
- **What:** Compressed summary of current conversation
- **Storage:** Generated on-the-fly, updated every ~5 messages
- **Purpose:** Maintain context when conversation exceeds buffer
- **Example:** "User has been asking about Batman's childhood and expressed sympathy for his loss."

### 3. Long-term Memory (Persistent Facts)
- **What:** Important facts extracted from conversations
- **Storage:** MongoDB + Qdrant (for semantic retrieval)
- **Types:**
  - User facts ("User's name is Sarah", "User is a teacher")
  - Preferences ("User prefers detailed answers")
  - Emotional moments ("User shared they lost their father too")
  - Character-specific ("User thinks Batman is too dark")
- **Retrieval:** Semantic search based on current message

### 4. Episodic Memory (Session Summaries)
- **What:** Summary of each past conversation session
- **Storage:** MongoDB
- **Purpose:** "Last time we spoke, you mentioned..."
- **Retrieval:** Most recent + semantically relevant

### 5. Entity Memory (Knowledge Graph)
- **What:** People, places, things the user has mentioned
- **Storage:** MongoDB (structured)
- **Purpose:** Track user's world (family, friends, interests)

## Context Assembly Algorithm

```python
def assemble_context(user_id, character, current_message):
    context = []
    token_budget = 4000  # Reserve for response
    
    # 1. Character Profile (always included)
    context.append(get_character_profile(character))  # ~500 tokens
    token_budget -= 500
    
    # 2. Entity Memory - User profile (always included)
    user_profile = get_user_entities(user_id, character)
    context.append(format_user_profile(user_profile))  # ~200 tokens
    token_budget -= 200
    
    # 3. Episodic Memory - Last session summary (if exists)
    last_session = get_last_session_summary(user_id, character)
    if last_session:
        context.append(f"Last conversation: {last_session}")  # ~200 tokens
        token_budget -= 200
    
    # 4. Long-term Memory - Retrieve relevant facts
    relevant_memories = semantic_search(
        query=current_message,
        user_id=user_id,
        character=character,
        limit=5
    )
    context.append(format_memories(relevant_memories))  # ~300 tokens
    token_budget -= 300
    
    # 5. Working Memory - Current session summary (if long conversation)
    if session_message_count > 10:
        working_memory = get_working_memory(session_id)
        context.append(f"Conversation so far: {working_memory}")  # ~300 tokens
        token_budget -= 300
    
    # 6. Short-term Buffer - Recent messages (fill remaining budget)
    recent_messages = get_recent_messages(
        session_id,
        max_tokens=token_budget
    )
    context.append(format_messages(recent_messages))
    
    return context
```

## Memory Extraction Pipeline

After each message exchange:

```
User Message → LLM Response → Memory Extraction
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Extract Facts   Update Entities   Check Importance
                    │               │               │
                    ▼               ▼               ▼
              Long-term        Entity           Mark for
              Memory           Memory           Summarization
```

### Fact Extraction Prompt
```
Extract important facts about the user from this conversation:
- Personal information (name, job, location)
- Preferences and opinions
- Emotional states and experiences
- Questions they want answered
- Things they mentioned about themselves

Return as JSON array of facts with importance score (1-10).
```

## Summarization Strategy

### Working Memory Update (Every 5 messages)
```
Previous summary: {working_memory}
New messages: {last_5_messages}

Update the summary to include new important information.
Keep it under 100 words. Focus on:
- Main topics discussed
- User's emotional state
- Unresolved questions
- Key decisions or revelations
```

### Session End Summary
```
Summarize this conversation between {user} and {character}:
{full_conversation}

Create a brief summary (2-3 sentences) capturing:
- Main topics discussed
- User's mood/intent
- Any promises or plans made
- Emotional high points
```

## MongoDB Schemas

### memories collection
```javascript
{
  _id: ObjectId,
  user_id: string,
  character_name: string,
  
  // Memory content
  type: "fact" | "preference" | "emotion" | "event",
  content: string,
  
  // For semantic retrieval
  embedding: [float],  // Or store in Qdrant
  
  // Importance & recency
  importance: float,  // 0-1
  access_count: int,
  last_accessed: datetime,
  created_at: datetime,
  
  // Source tracking
  source_session_id: string,
  source_message_id: string
}
```

### sessions collection
```javascript
{
  _id: ObjectId,
  user_id: string,
  character_name: string,
  
  // Session data
  started_at: datetime,
  ended_at: datetime,
  message_count: int,
  
  // Summaries
  working_memory: string,  // Current summary
  final_summary: string,   // End of session
  
  // Messages (or reference to messages collection)
  messages: [
    {
      role: "user" | "assistant",
      content: string,
      timestamp: datetime,
      tokens: int
    }
  ]
}
```

### entities collection
```javascript
{
  _id: ObjectId,
  user_id: string,
  character_name: string,  // null for global entities
  
  entity_type: "person" | "place" | "thing" | "event",
  name: string,
  attributes: {
    relationship: string,  // "user's sister"
    details: string
  },
  
  first_mentioned: datetime,
  last_mentioned: datetime,
  mention_count: int
}
```

## Token Budget Management

```
Total Context Window: 8000 tokens (GPT-4o-mini)
Reserved for Response: 1000 tokens
Available for Context: 7000 tokens

Allocation:
├── System Prompt:        500 tokens (fixed)
├── Character Profile:    500 tokens (fixed)
├── User Profile:         200 tokens (fixed)
├── Retrieved Memories:   500 tokens (variable)
├── Episodic (last):      200 tokens (optional)
├── Working Memory:       300 tokens (if needed)
└── Message Buffer:      ~4800 tokens (fills remainder)

Message buffer can hold ~15-20 message exchanges
```

## Attention Refresh Mechanism

Similar to how attention works in transformers, we refresh context relevance:

1. **Recency Attention:** Recent messages always have full weight
2. **Semantic Attention:** Retrieve memories similar to current query
3. **Importance Attention:** High-importance facts always included
4. **Decay Function:** Older, unaccessed memories fade

```python
def calculate_memory_relevance(memory, current_query, current_time):
    # Semantic similarity (0-1)
    semantic_score = cosine_similarity(
        embed(memory.content), 
        embed(current_query)
    )
    
    # Recency decay (half-life of 7 days)
    days_old = (current_time - memory.last_accessed).days
    recency_score = 0.5 ** (days_old / 7)
    
    # Importance weight
    importance_score = memory.importance
    
    # Access frequency boost
    frequency_boost = min(memory.access_count / 10, 1.0)
    
    # Combined score
    return (
        semantic_score * 0.4 +
        recency_score * 0.2 +
        importance_score * 0.3 +
        frequency_boost * 0.1
    )
```

## Implementation Files

```
app/memory/
├── __init__.py
├── models.py           # Memory domain models
├── schemas.py          # Pydantic schemas
├── repository.py       # MongoDB operations
├── embedding.py        # Vector operations
├── extraction.py       # Fact extraction from conversations
├── summarization.py    # Working memory & session summaries
├── context_manager.py  # Context assembly & token management
└── service.py          # Main memory service
```

