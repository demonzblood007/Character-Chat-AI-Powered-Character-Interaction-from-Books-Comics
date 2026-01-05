"""
Character API Schemas
=====================

Request and response models for character endpoints.
Kept simple - users shouldn't need documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────────

class CreatePersonaRequest(BaseModel):
    """Persona details for character creation."""
    description: str = Field(..., min_length=10, max_length=1000)
    personality: str = Field(..., min_length=10, max_length=500)
    speaking_style: str = Field(..., min_length=10, max_length=500)
    example_messages: List[str] = Field(default_factory=list, max_length=5)
    greeting: str = Field(..., min_length=5, max_length=300)
    conversation_starters: List[str] = Field(default_factory=list, max_length=5)
    topics_to_embrace: List[str] = Field(default_factory=list)
    topics_to_avoid: List[str] = Field(default_factory=list)


class CreateCharacterRequest(BaseModel):
    """Request to create a new character."""
    name: str = Field(..., min_length=1, max_length=100)
    tagline: str = Field(..., min_length=5, max_length=150)
    category: str = Field(default="original")
    tags: List[str] = Field(default_factory=list, max_length=5)
    source: Optional[str] = Field(None, max_length=200)
    author: Optional[str] = Field(None, max_length=100)
    visibility: str = Field(default="private")  # private, public, unlisted
    avatar_url: Optional[str] = None
    persona: CreatePersonaRequest
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Captain Nemo",
                "tagline": "A mysterious captain of the deep seas",
                "category": "classic_literature",
                "tags": ["submarine", "mysterious", "adventurer"],
                "source": "Twenty Thousand Leagues Under the Sea",
                "author": "Jules Verne",
                "visibility": "private",
                "persona": {
                    "description": "A brilliant but enigmatic captain who commands the Nautilus submarine. Has rejected surface civilization and lives beneath the waves.",
                    "personality": "Intelligent, mysterious, passionate about the sea, bitter toward humanity, cultured, generous to guests",
                    "speaking_style": "Formal and eloquent. Speaks of the sea with reverence. Occasionally cryptic about his past.",
                    "example_messages": [
                        "The sea is everything. It covers seven-tenths of the terrestrial globe.",
                        "You are aboard the Nautilus. I am Captain Nemo.",
                    ],
                    "greeting": "Welcome aboard the Nautilus. Few surface dwellers have seen what you are about to see.",
                    "conversation_starters": [
                        "Tell me about the Nautilus",
                        "Why did you leave the surface world?",
                        "What wonders have you seen in the deep?",
                    ],
                    "topics_to_embrace": ["the sea", "marine life", "science", "freedom"],
                    "topics_to_avoid": ["his past identity", "surface politics"],
                }
            }
        }


class CreateFromTemplateRequest(BaseModel):
    """Request to create character from a template."""
    template_id: str = Field(..., description="Template to use")
    name: str = Field(..., min_length=1, max_length=100)
    tagline: str = Field(..., min_length=5, max_length=150)
    customizations: Optional[Dict[str, Any]] = Field(
        None,
        description="Override specific persona fields"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "wise_mentor",
                "name": "Master Yoda",
                "tagline": "Do or do not, there is no try",
                "customizations": {
                    "speaking_style": "Inverted sentence structure. Cryptic wisdom. References the Force.",
                    "topics_to_embrace": ["the Force", "patience", "training"],
                }
            }
        }


class UpdateCharacterRequest(BaseModel):
    """Request to update a character."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    tagline: Optional[str] = Field(None, min_length=5, max_length=150)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: Optional[str] = None
    avatar_url: Optional[str] = None
    persona: Optional[CreatePersonaRequest] = None


# ─────────────────────────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────────────────────────

class CharacterCard(BaseModel):
    """Character summary for listing."""
    id: str
    name: str
    tagline: str
    avatar_url: str
    category: str
    source: Optional[str] = None
    chat_count: int = 0
    favorite_count: int = 0
    is_official: bool = False


class CharacterDetail(BaseModel):
    """Full character details."""
    id: str
    name: str
    tagline: str
    avatar_url: str
    category: str
    tags: List[str]
    source: Optional[str]
    author: Optional[str]
    creator_id: str
    visibility: str
    is_official: bool
    chat_count: int
    favorite_count: int
    persona: Dict[str, Any]
    created_at: str
    
    # User-specific
    is_favorite: bool = False
    is_mine: bool = False


class CharacterListResponse(BaseModel):
    """Paginated list of characters."""
    characters: List[CharacterCard]
    total: int
    page: int
    page_size: int
    total_pages: int


class FeaturedResponse(BaseModel):
    """Featured characters for homepage."""
    popular: List[CharacterCard]
    by_category: Dict[str, List[CharacterCard]]


class CategoryInfo(BaseModel):
    """Category with count."""
    id: str
    name: str
    count: int


class TemplateInfo(BaseModel):
    """Template summary."""
    id: str
    name: str
    description: str
    category: str
    customization_tips: List[str]


class TemplateDetail(BaseModel):
    """Full template with defaults."""
    id: str
    name: str
    description: str
    category: str
    customization_tips: List[str]
    default_persona: Dict[str, Any]

