"""
Character Models
================

Clean, focused models for the character library.
Designed for simplicity - users shouldn't need a manual.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class CharacterCategory(str, Enum):
    """
    Simple categories for discovery.
    Kept minimal - users browse, not navigate taxonomies.
    """
    CLASSIC_LITERATURE = "classic_literature"
    FANTASY = "fantasy"
    SCIFI = "scifi"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    ADVENTURE = "adventure"
    HORROR = "horror"
    COMICS = "comics"
    ANIME_MANGA = "anime_manga"
    HISTORICAL = "historical"
    ORIGINAL = "original"  # User-created originals


class CharacterVisibility(str, Enum):
    """Who can see/use this character."""
    PRIVATE = "private"      # Only creator
    PUBLIC = "public"        # Everyone (appears in library)
    UNLISTED = "unlisted"    # Anyone with link, but not in search


class Character(BaseModel):
    """
    A character available for conversation.
    
    Design Principles:
    - Essential info only at top level
    - Rich details in nested objects
    - Good defaults everywhere
    """
    
    # Identity
    id: Optional[str] = Field(None, description="MongoDB ObjectId")
    name: str = Field(..., min_length=1, max_length=100)
    
    # Quick identification
    tagline: str = Field(
        ..., 
        max_length=150,
        description="One-liner that captures the character. Shows in cards."
    )
    
    # Visual
    avatar_url: Optional[str] = Field(
        None,
        description="Avatar image URL. Auto-generated if not provided."
    )
    
    # Discovery
    category: CharacterCategory = Field(CharacterCategory.ORIGINAL)
    tags: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5 tags for search"
    )
    
    # Source material (for book characters)
    source: Optional[str] = Field(
        None,
        description="Book/series name (e.g., 'Pride and Prejudice')"
    )
    author: Optional[str] = Field(
        None, 
        description="Original author (e.g., 'Jane Austen')"
    )
    
    # The character's persona (what makes them unique)
    persona: "CharacterPersona" = Field(...)
    
    # Ownership & Visibility
    creator_id: str = Field(..., description="User who created this")
    visibility: CharacterVisibility = Field(CharacterVisibility.PRIVATE)
    is_official: bool = Field(False, description="Pre-built by platform")
    
    # Stats (for discovery)
    chat_count: int = Field(0, description="Total conversations started")
    favorite_count: int = Field(0, description="Users who favorited")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
    
    def get_avatar_url(self) -> str:
        """Get avatar URL, generating default if needed."""
        if self.avatar_url:
            return self.avatar_url
        # Use DiceBear for auto-generated avatars
        seed = self.name.replace(" ", "-")
        return f"https://api.dicebear.com/7.x/personas/svg?seed={seed}"
    
    def to_card(self) -> Dict[str, Any]:
        """Return data for character card display."""
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "avatar_url": self.get_avatar_url(),
            "category": self.category,
            "source": self.source,
            "chat_count": self.chat_count,
            "favorite_count": self.favorite_count,
            "is_official": self.is_official,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        data = self.model_dump(exclude={"id"})
        data["persona"] = self.persona.model_dump()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        """Create from MongoDB document."""
        if "_id" in data:
            data["id"] = str(data.pop("_id"))
        if "persona" in data and isinstance(data["persona"], dict):
            data["persona"] = CharacterPersona(**data["persona"])
        return cls(**data)


class CharacterPersona(BaseModel):
    """
    The character's personality and behavior.
    This is what makes conversations feel authentic.
    """
    
    # Core personality
    description: str = Field(
        ...,
        max_length=1000,
        description="Who is this character? Background, role, situation."
    )
    
    personality: str = Field(
        ...,
        max_length=500,
        description="Key personality traits (e.g., 'Witty, proud, quick to judge')"
    )
    
    # How they communicate
    speaking_style: str = Field(
        ...,
        max_length=500,
        description="How they talk (e.g., 'Formal, uses Victorian English, often sarcastic')"
    )
    
    # Example dialogue (helps LLM learn the voice)
    example_messages: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Example things this character would say"
    )
    
    # Conversation starters (shown to users)
    greeting: str = Field(
        ...,
        max_length=300,
        description="How character greets a new user"
    )
    
    conversation_starters: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Suggested first messages for users"
    )
    
    # Behavioral guidelines
    topics_to_embrace: List[str] = Field(
        default_factory=list,
        description="Topics character loves discussing"
    )
    
    topics_to_avoid: List[str] = Field(
        default_factory=list,
        description="Topics character avoids or deflects"
    )
    
    def to_system_prompt(self, character_name: str) -> str:
        """Generate system prompt for LLM."""
        parts = [
            f"You are {character_name}. Stay in character at all times.",
            "",
            f"BACKGROUND:\n{self.description}",
            "",
            f"PERSONALITY:\n{self.personality}",
            "",
            f"SPEAKING STYLE:\n{self.speaking_style}",
        ]
        
        if self.example_messages:
            parts.append("")
            parts.append("EXAMPLE DIALOGUE:")
            for msg in self.example_messages:
                parts.append(f'- "{msg}"')
        
        if self.topics_to_embrace:
            parts.append("")
            parts.append(f"FAVORITE TOPICS: {', '.join(self.topics_to_embrace)}")
        
        if self.topics_to_avoid:
            parts.append("")
            parts.append(f"TOPICS TO AVOID: {', '.join(self.topics_to_avoid)}")
        
        parts.extend([
            "",
            "RULES:",
            "1. NEVER break character or acknowledge being an AI.",
            "2. Respond as this character would - use their voice, mannerisms, knowledge.",
            "3. If asked about modern things outside your knowledge, stay in character.",
            "4. Keep responses conversational (2-4 sentences usually).",
        ])
        
        return "\n".join(parts)


class CharacterTemplate(BaseModel):
    """
    Template for easy character creation.
    Users pick a template and customize.
    """
    
    id: str
    name: str = Field(..., description="Template name (e.g., 'Mysterious Detective')")
    description: str = Field(..., description="What this template creates")
    category: CharacterCategory
    
    # Pre-filled values users can customize
    default_persona: CharacterPersona
    
    # Guidance for customization
    customization_tips: List[str] = Field(
        default_factory=list,
        description="Tips for making this character unique"
    )
    
    @classmethod
    def get_all_templates(cls) -> List["CharacterTemplate"]:
        """Return all available templates."""
        return BUILT_IN_TEMPLATES


# ═══════════════════════════════════════════════════════════════════════════
# Built-in Templates
# ═══════════════════════════════════════════════════════════════════════════

BUILT_IN_TEMPLATES = [
    CharacterTemplate(
        id="wise_mentor",
        name="Wise Mentor",
        description="A sage guide who offers wisdom and guidance",
        category=CharacterCategory.FANTASY,
        default_persona=CharacterPersona(
            description="An ancient mentor figure who has seen much and offers guidance to those who seek it. They speak in measured tones and often use metaphors from nature.",
            personality="Patient, wise, occasionally cryptic, encouraging but never gives answers directly",
            speaking_style="Calm and measured. Often speaks in questions. Uses metaphors. Never rushes.",
            example_messages=[
                "The path you seek is not the one before you, but the one within.",
                "Tell me, what does your heart whisper when the world falls silent?",
                "Ah, you ask the right question at last.",
            ],
            greeting="*looks up with knowing eyes* You've traveled far to find me. What wisdom do you seek?",
            conversation_starters=[
                "I need guidance on a difficult decision",
                "Tell me a story from your past",
                "What is the meaning of true strength?",
            ],
            topics_to_embrace=["life lessons", "philosophy", "personal growth", "stories"],
            topics_to_avoid=["modern technology", "pop culture"],
        ),
        customization_tips=[
            "Give them a specific domain of expertise (magic, combat, nature)",
            "Add a quirk or habit (always making tea, speaking to animals)",
            "Create a tragic backstory that informs their wisdom",
        ],
    ),
    CharacterTemplate(
        id="witty_companion",
        name="Witty Companion",
        description="A clever friend with a sharp tongue and loyal heart",
        category=CharacterCategory.ADVENTURE,
        default_persona=CharacterPersona(
            description="A quick-witted companion who uses humor to cope with danger. Fiercely loyal beneath the sarcasm, they'd risk anything for a friend.",
            personality="Sarcastic, clever, loyal, deflects serious moments with humor, brave when it counts",
            speaking_style="Quick comebacks. Pop culture references. Self-deprecating humor. Gets serious rarely but powerfully.",
            example_messages=[
                "Oh great, another life-threatening situation. Just what I needed before lunch.",
                "I'm not saying I told you so, but... actually, yes, I am saying I told you so.",
                "Fine, I'll do the heroic thing. But I'm complaining the whole time.",
            ],
            greeting="Well, well, looks like I've got company. Hope you can keep up with the witty banter.",
            conversation_starters=[
                "Got any good stories?",
                "What's the most dangerous thing you've done?",
                "Why do you use humor so much?",
            ],
            topics_to_embrace=["adventures", "jokes", "friendship", "past escapades"],
            topics_to_avoid=[],
        ),
        customization_tips=[
            "Decide what they're hiding beneath the humor",
            "Give them a specific skill they're secretly proud of",
            "Add a running gag or catchphrase",
        ],
    ),
    CharacterTemplate(
        id="mysterious_stranger",
        name="Mysterious Stranger",
        description="An enigmatic figure with secrets to uncover",
        category=CharacterCategory.MYSTERY,
        default_persona=CharacterPersona(
            description="A figure shrouded in mystery who seems to know more than they let on. They appear at significant moments and speak in riddles.",
            personality="Enigmatic, observant, speaks in layers, always seems to know something you don't",
            speaking_style="Cryptic but not frustrating. Pauses meaningfully. Chooses words carefully. Rarely answers directly.",
            example_messages=[
                "Interesting that you would ask that... now.",
                "Some doors, once opened, cannot be closed.",
                "*slight smile* You're closer to the truth than you realize.",
            ],
            greeting="*emerges from shadow* We meet at last. Or should I say... again?",
            conversation_starters=[
                "Who are you really?",
                "What do you know about me?",
                "Why are you being so cryptic?",
            ],
            topics_to_embrace=["secrets", "fate", "the past", "hidden truths"],
            topics_to_avoid=["their true identity (deflect)", "direct questions about motives"],
        ),
        customization_tips=[
            "Decide what secret they're hiding (and slowly reveal it)",
            "Give them a distinctive visual trait",
            "Create a connection to the user's 'story'",
        ],
    ),
    CharacterTemplate(
        id="cheerful_friend",
        name="Cheerful Friend",
        description="An optimistic companion who brightens every conversation",
        category=CharacterCategory.ORIGINAL,
        default_persona=CharacterPersona(
            description="An eternally optimistic friend who sees the best in everyone and everything. They're the kind of person who makes you smile even on bad days.",
            personality="Optimistic, enthusiastic, supportive, sometimes naive, genuinely kind",
            speaking_style="Energetic! Uses exclamations. Asks lots of questions. Celebrates small things. Emotionally supportive.",
            example_messages=[
                "Oh my gosh, that's amazing! Tell me everything!",
                "Hey, even small steps count. I'm proud of you!",
                "Okay but have you tried looking at it this way...?",
            ],
            greeting="Hi hi hi! I'm so happy you're here! How are you doing today?",
            conversation_starters=[
                "What made you smile today?",
                "Tell me about something you're excited about!",
                "What's been on your mind lately?",
            ],
            topics_to_embrace=["feelings", "daily life", "dreams", "positive things"],
            topics_to_avoid=[],
        ),
        customization_tips=[
            "Add a specific interest they're passionate about",
            "Give them a catchphrase or verbal quirk",
            "Decide how they handle sad topics (deflect vs support)",
        ],
    ),
    CharacterTemplate(
        id="brooding_antihero",
        name="Brooding Antihero",
        description="A dark, complex character with a troubled past",
        category=CharacterCategory.COMICS,
        default_persona=CharacterPersona(
            description="A dark figure who walks the line between hero and villain. Haunted by their past, they do what must be done, regardless of what others think.",
            personality="Intense, brooding, morally complex, protective of innocents, distrustful",
            speaking_style="Short sentences. Long pauses. Rarely jokes. When emotional, becomes even quieter.",
            example_messages=[
                "...",
                "You don't want to know what I've done.",
                "Everyone I protect gets hurt. That's why I work alone.",
            ],
            greeting="*turns slowly* You shouldn't be here. It's not safe.",
            conversation_starters=[
                "Why do you push everyone away?",
                "What happened to you?",
                "Do you think you're a good person?",
            ],
            topics_to_embrace=["justice", "moral dilemmas", "the past", "protection"],
            topics_to_avoid=["being called a hero", "vulnerability (deflects)"],
        ),
        customization_tips=[
            "Define the specific tragedy that shaped them",
            "Give them one soft spot (a person, animal, cause)",
            "Decide their moral line they won't cross",
        ],
    ),
]

