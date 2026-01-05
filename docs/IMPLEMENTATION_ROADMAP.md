# Implementation Roadmap: Unique Features

## Phase 1: Core Differentiators (Weeks 1-4)

### Feature 1.1: Cross-Character Memory (Within Same Book)

**Goal:** Characters know what you've discussed with other characters from the same source material.

**Technical Design:**

#### Database Schema Changes
```python
# app/memory/models.py - Update Memory model
class Memory:
    # ... existing fields ...
    universe_id: Optional[str] = None  # Links characters from same book/source
    is_shared: bool = False  # Whether this memory should be visible to other characters
```

#### Context Manager Updates
```python
# app/memory/context_manager.py
async def assemble_context(...):
    # ... existing code ...
    
    # NEW: Get memories from other characters in same universe
    if character.universe_id:
        related_memories = await self._memory_repo.get_universe_memories(
            user_id=user_id,
            universe_id=character.universe_id,
            exclude_character=character_name,
            query=current_message,
            limit=3
        )
        # Add to context with attribution: "From conversations with [Other Character]..."
```

#### Repository Method
```python
# app/memory/repository.py
async def get_universe_memories(
    self,
    user_id: str,
    universe_id: str,
    exclude_character: str,
    query: str,
    limit: int = 3
) -> List[Memory]:
    """Get relevant memories from other characters in same universe."""
    # 1. Find all characters in this universe
    # 2. Get their memories
    # 3. Semantic search to find relevant ones
    # 4. Return top N
```

**Implementation Steps:**
1. Add `universe_id` to Character model (derive from `source` field or file_id)
2. Update Memory model with `universe_id` and `is_shared`
3. Modify memory extraction to include `universe_id`
4. Update context manager to fetch cross-character memories
5. Format cross-character memories in prompts with attribution

**Testing:**
- Upload a book with multiple characters
- Tell Character A about yourself
- Chat with Character B → Should reference what you told Character A

---

### Feature 1.2: Narrative Threads

**Goal:** Track ongoing storylines that persist across sessions.

**Technical Design:**

#### New Model
```python
# app/memory/models.py
class NarrativeThread(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    summary: str
    characters_involved: List[str]
    status: str  # "active", "resolved", "archived"
    started_at: datetime
    last_updated: datetime
    related_memories: List[str]  # Memory IDs
    related_sessions: List[str]  # Session IDs
```

#### Thread Detection
```python
# app/memory/extraction.py
class ThreadDetector:
    """Detects when user starts/continues/resolves narrative threads."""
    
    async def detect_thread_updates(
        self,
        session: Session,
        recent_messages: List[Message]
    ) -> List[ThreadUpdate]:
        """Analyze messages to detect thread activity."""
        # Use LLM to detect:
        # - New thread started ("Let's solve this mystery...")
        # - Thread continued ("Remember that case we were working on?")
        # - Thread resolved ("The mystery is solved!")
```

#### Context Integration
```python
# app/memory/context_manager.py
async def assemble_context(...):
    # ... existing code ...
    
    # NEW: Get active narrative threads
    active_threads = await self._thread_repo.get_active_threads(
        user_id=user_id,
        character_name=character_name
    )
    if active_threads:
        thread_context = format_threads(active_threads)
        # Add to context
```

**Implementation Steps:**
1. Create `NarrativeThread` model
2. Create `ThreadRepository` for MongoDB
3. Implement `ThreadDetector` using LLM
4. Update memory service to track threads
5. Integrate threads into context assembly
6. Create API endpoint: `GET /narrative/threads`

**Testing:**
- Start a conversation with a character about solving a mystery
- System should create a thread
- In next session, character should reference the thread

---

### Feature 1.3: Character Evolution (Trait Tracking)

**Goal:** Characters gradually change based on long-term interactions.

**Technical Design:**

#### Character Trait Model
```python
# app/characters/models.py
class CharacterTrait(BaseModel):
    name: str  # "optimism", "brooding", "humor"
    value: float  # 0.0 to 1.0
    base_value: float  # Original value from persona
    change_rate: float = 0.01  # How fast it changes per positive interaction

class CharacterEvolution(BaseModel):
    character_id: str
    traits: Dict[str, CharacterTrait]
    interaction_count: int
    last_updated: datetime
    evolution_history: List[Dict]  # Timestamp, trait values
```

#### Evolution Engine
```python
# app/characters/evolution.py
class CharacterEvolutionService:
    """Manages character trait evolution based on interactions."""
    
    async def update_character(
        self,
        character_id: str,
        session: Session,
        sentiment: float  # -1 to +1
    ):
        """Update character traits based on conversation sentiment."""
        # Analyze conversation
        # Determine which traits should shift
        # Update trait values gradually
        # Store evolution history
```

#### Persona Updates
```python
# app/characters/service.py
def get_evolved_persona(character: Character) -> CharacterPersona:
    """Generate persona with evolved traits applied."""
    # Take base persona
    # Adjust based on current trait values
    # Return modified persona
```

**Implementation Steps:**
1. Add `CharacterEvolution` model
2. Create `EvolutionRepository`
3. Implement sentiment analysis for conversations
4. Build trait update logic
5. Modify persona generation to use evolved traits
6. Create API endpoint: `GET /characters/{id}/evolution`

**Testing:**
- Have 20 positive conversations with a brooding character
- Check evolution endpoint → Optimism trait should increase
- Next conversation should reflect change

---

## Phase 2: Engagement Boosters (Weeks 5-8)

### Feature 2.1: Multi-Character Conversations

**Goal:** Chat with multiple characters simultaneously.

**Technical Design:**

#### Group Session Model
```python
# app/chat/models.py
class GroupSession(BaseModel):
    id: Optional[str] = None
    user_id: str
    character_names: List[str]  # Multiple characters
    messages: List[GroupMessage]
    turn_order: List[str]  # Which character responds next
    started_at: datetime

class GroupMessage(BaseModel):
    role: str  # "user" or character name
    content: str
    timestamp: datetime
```

#### Turn Management
```python
# app/chat/group_service.py
class GroupChatService:
    """Manages multi-character conversations."""
    
    async def process_user_message(
        self,
        session_id: str,
        message: str
    ) -> List[CharacterResponse]:
        """Process user message, get responses from all characters."""
        # 1. Assemble context for each character
        # 2. Each character responds to user + sees other characters' responses
        # 3. Return list of responses
        # 4. Update each character's memory
```

**Implementation Steps:**
1. Create `GroupSession` and `GroupMessage` models
2. Build `GroupChatService`
3. Create endpoint: `POST /chat/group`
4. Frontend: Show multiple character responses in UI

---

### Feature 2.2: User Story Timeline

**Goal:** Visual timeline of user's journey with characters.

**Technical Design:**

#### Timeline Event Model
```python
# app/timeline/models.py
class TimelineEvent(BaseModel):
    id: str
    user_id: str
    event_type: str  # "session_start", "thread_start", "memory_created", "relationship_changed"
    character_name: Optional[str]
    title: str
    description: str
    timestamp: datetime
    metadata: Dict
```

#### Timeline Generator
```python
# app/timeline/service.py
class TimelineService:
    """Generates timeline from sessions, memories, and threads."""
    
    async def generate_timeline(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TimelineEvent]:
        """Aggregate all user activity into timeline."""
        # 1. Get all sessions
        # 2. Get narrative threads
        # 3. Get key memories
        # 4. Generate events
        # 5. Sort by timestamp
```

**Implementation Steps:**
1. Create `TimelineEvent` model
2. Build `TimelineService`
3. Create endpoint: `GET /timeline`
4. Frontend: Render timeline visualization

---

## Implementation Priority

### Week 1-2: Cross-Character Memory
- Highest impact
- Uses existing memory system
- Immediate visible value

### Week 3: Narrative Threads
- Medium complexity
- Leverages episodic memory
- Clear user value

### Week 4: Character Evolution (MVP)
- Start with simple trait tracking
- Can expand later

### Week 5-6: Multi-Character Conversations
- Requires significant frontend work
- High engagement potential

### Week 7-8: Story Timeline
- Good for retention
- Showcases value of memory system

---

## Technical Considerations

### Performance
- Cross-character memory adds queries → Cache aggressively
- Narrative threads need efficient detection → Batch process after sessions
- Evolution calculations → Background job, not real-time

### Privacy
- Cross-character memory opt-in by default
- Users can disable per-character or globally
- Clear privacy settings UI

### Scalability
- Timeline generation can be expensive → Pre-compute and cache
- Group chats multiply LLM calls → Optimize with batching
- Evolution history grows → Archive old data

---

## Success Metrics Per Feature

### Cross-Character Memory
- % of users who have multi-character conversations
- User satisfaction with memory consistency

### Narrative Threads
- % of users who start at least one thread
- Average thread length (sessions)
- Thread completion rate

### Character Evolution
- % of characters that show meaningful evolution
- User perception of character growth

### Multi-Character Conversations
- % of users who try group chats
- Average messages per group session
- Return rate for group chat users

---

## Next Immediate Steps

1. **Design Review:** Review this roadmap with team
2. **Database Migration:** Add new fields to existing models
3. **Start Feature 1.1:** Cross-character memory (highest ROI)
4. **Build in Public:** Share progress, gather feedback
5. **Measure Everything:** Track metrics from day one

---

**Remember: Ship incrementally. Each feature should work standalone, then integrate.**

