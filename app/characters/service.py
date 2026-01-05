"""
Character Service
=================

Business logic for character management.
Handles creation, discovery, and user interactions.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from .models import (
    Character, CharacterPersona, CharacterTemplate, 
    CharacterCategory, CharacterVisibility, BUILT_IN_TEMPLATES
)
from .repository import CharacterRepository
from .prebuilt import get_prebuilt_characters, SYSTEM_USER_ID


# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/character_chat")
MONGODB_DB = os.getenv("MONGODB_DB", "character_chat")


class CharacterService:
    """
    Service for character management.
    
    Provides:
    - Character creation (from scratch or template)
    - Discovery (search, browse, popular)
    - User interactions (favorites, recent)
    - Pre-built character seeding
    """
    
    def __init__(self, db=None):
        """Initialize character service."""
        self._db = db
        self._repo: Optional[CharacterRepository] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize service and seed pre-built characters."""
        if self._initialized:
            return
        
        # Get database
        if self._db is None:
            client = AsyncIOMotorClient(MONGODB_URI)
            self._db = client[MONGODB_DB]
        
        self._repo = CharacterRepository(self._db)
        await self._repo.ensure_indexes()
        
        # Seed pre-built characters
        await self._seed_prebuilt_characters()
        
        self._initialized = True
    
    async def _seed_prebuilt_characters(self):
        """Seed pre-built characters if they don't exist."""
        for character in get_prebuilt_characters():
            # Check if already exists
            existing = await self._repo.get_by_name_and_user(
                character.name, SYSTEM_USER_ID
            )
            
            if existing is None:
                character.creator_id = SYSTEM_USER_ID
                character.is_official = True
                character.visibility = CharacterVisibility.PUBLIC
                await self._repo.create(character)
                print(f"  → Seeded character: {character.name}")
    
    # ─────────────────────────────────────────────────────────────────
    # Character Creation
    # ─────────────────────────────────────────────────────────────────
    
    async def create_character(
        self,
        user_id: str,
        name: str,
        tagline: str,
        persona: CharacterPersona,
        category: CharacterCategory = CharacterCategory.ORIGINAL,
        tags: List[str] = None,
        source: Optional[str] = None,
        author: Optional[str] = None,
        visibility: CharacterVisibility = CharacterVisibility.PRIVATE,
        avatar_url: Optional[str] = None,
    ) -> Character:
        """
        Create a new character.
        
        Args:
            user_id: Creator's ID
            name: Character name
            tagline: Short description
            persona: Character's personality
            category: Category for discovery
            tags: Search tags
            source: Source material
            author: Original author
            visibility: Who can see/use
            avatar_url: Custom avatar
            
        Returns:
            Created character
        """
        await self.initialize()
        
        character = Character(
            name=name,
            tagline=tagline,
            persona=persona,
            category=category,
            tags=tags or [],
            source=source,
            author=author,
            creator_id=user_id,
            visibility=visibility,
            avatar_url=avatar_url,
            is_official=False,
        )
        
        return await self._repo.create(character)
    
    async def create_from_template(
        self,
        user_id: str,
        template_id: str,
        name: str,
        tagline: str,
        customizations: Dict[str, Any] = None,
    ) -> Character:
        """
        Create character from a template.
        
        Args:
            user_id: Creator's ID
            template_id: Template to use
            name: Character name
            tagline: Short description
            customizations: Overrides for persona fields
            
        Returns:
            Created character
        """
        await self.initialize()
        
        # Find template
        template = next(
            (t for t in BUILT_IN_TEMPLATES if t.id == template_id),
            None
        )
        
        if template is None:
            raise ValueError(f"Template not found: {template_id}")
        
        # Start with template persona
        persona_dict = template.default_persona.model_dump()
        
        # Apply customizations
        if customizations:
            for key, value in customizations.items():
                if key in persona_dict and value:
                    persona_dict[key] = value
        
        persona = CharacterPersona(**persona_dict)
        
        # Create character
        return await self.create_character(
            user_id=user_id,
            name=name,
            tagline=tagline,
            persona=persona,
            category=template.category,
        )
    
    # ─────────────────────────────────────────────────────────────────
    # Character Retrieval
    # ─────────────────────────────────────────────────────────────────
    
    async def get_character(
        self,
        character_id: str,
        user_id: str,
    ) -> Optional[Character]:
        """
        Get a character by ID.
        
        Returns None if character doesn't exist or user can't access it.
        """
        await self.initialize()
        
        character = await self._repo.get_by_id(character_id)
        
        if character is None:
            return None
        
        # Check access
        if not self._can_access(character, user_id):
            return None
        
        return character
    
    async def get_character_for_chat(
        self,
        character_name: str,
        user_id: str,
    ) -> Optional[Character]:
        """
        Get a character by name for chat.
        
        Searches user's characters first, then public library.
        """
        await self.initialize()
        
        return await self._repo.get_by_name_and_user(character_name, user_id)
    
    def _can_access(self, character: Character, user_id: str) -> bool:
        """Check if user can access character."""
        if character.creator_id == user_id:
            return True
        if character.visibility == CharacterVisibility.PUBLIC:
            return True
        if character.visibility == CharacterVisibility.UNLISTED:
            return True  # Anyone with the ID can access
        return False
    
    # ─────────────────────────────────────────────────────────────────
    # Discovery
    # ─────────────────────────────────────────────────────────────────
    
    async def search_characters(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        official_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Search public characters.
        
        Returns:
            Dict with characters, total, page info
        """
        await self.initialize()
        
        category_enum = None
        if category:
            try:
                category_enum = CharacterCategory(category)
            except ValueError:
                pass
        
        skip = (page - 1) * page_size
        
        characters, total = await self._repo.search(
            query=query,
            category=category_enum,
            official_only=official_only,
            limit=page_size,
            skip=skip,
        )
        
        return {
            "characters": [c.to_card() for c in characters],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    async def get_featured_characters(self) -> Dict[str, Any]:
        """
        Get featured characters for homepage.
        
        Returns curated selection of official characters.
        """
        await self.initialize()
        
        # Get popular official characters
        popular = await self._repo.get_popular_characters(limit=6)
        
        # Get by category
        categories = {}
        for category in [
            CharacterCategory.CLASSIC_LITERATURE,
            CharacterCategory.FANTASY,
            CharacterCategory.COMICS,
        ]:
            chars = await self._repo.get_by_category(category, limit=4)
            if chars:
                categories[category.value] = [c.to_card() for c in chars]
        
        return {
            "popular": [c.to_card() for c in popular],
            "by_category": categories,
        }
    
    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with counts."""
        await self.initialize()
        
        categories = []
        for category in CharacterCategory:
            chars = await self._repo.get_by_category(category, limit=1)
            count = len(await self._repo.get_by_category(category, limit=100))
            
            categories.append({
                "id": category.value,
                "name": category.value.replace("_", " ").title(),
                "count": count,
            })
        
        return [c for c in categories if c["count"] > 0]
    
    # ─────────────────────────────────────────────────────────────────
    # User Collections
    # ─────────────────────────────────────────────────────────────────
    
    async def get_my_characters(self, user_id: str) -> List[Dict[str, Any]]:
        """Get characters created by user."""
        await self.initialize()
        
        characters = await self._repo.get_user_characters(user_id)
        return [c.to_card() for c in characters]
    
    async def get_my_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's favorite characters."""
        await self.initialize()
        
        characters = await self._repo.get_user_favorites(user_id)
        return [c.to_card() for c in characters]
    
    async def add_to_favorites(self, user_id: str, character_id: str) -> bool:
        """Add character to favorites."""
        await self.initialize()
        return await self._repo.add_favorite(user_id, character_id)
    
    async def remove_from_favorites(self, user_id: str, character_id: str) -> bool:
        """Remove character from favorites."""
        await self.initialize()
        return await self._repo.remove_favorite(user_id, character_id)
    
    # ─────────────────────────────────────────────────────────────────
    # Character Management
    # ─────────────────────────────────────────────────────────────────
    
    async def update_character(
        self,
        user_id: str,
        character_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Character]:
        """
        Update a character.
        
        Only the creator can update their characters.
        """
        await self.initialize()
        
        character = await self._repo.get_by_id(character_id)
        
        if character is None:
            return None
        
        if character.creator_id != user_id:
            raise PermissionError("You can only edit your own characters")
        
        if character.is_official:
            raise PermissionError("Official characters cannot be edited")
        
        # Apply updates
        allowed_fields = [
            "name", "tagline", "category", "tags", "source", 
            "author", "visibility", "avatar_url", "persona"
        ]
        
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                if field == "persona" and isinstance(value, dict):
                    value = CharacterPersona(**value)
                setattr(character, field, value)
        
        return await self._repo.update(character)
    
    async def delete_character(
        self,
        user_id: str,
        character_id: str,
    ) -> bool:
        """Delete a character (only own characters)."""
        await self.initialize()
        return await self._repo.delete(character_id, user_id)
    
    # ─────────────────────────────────────────────────────────────────
    # Templates
    # ─────────────────────────────────────────────────────────────────
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get all available templates."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "customization_tips": t.customization_tips,
            }
            for t in BUILT_IN_TEMPLATES
        ]
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template with full details."""
        template = next(
            (t for t in BUILT_IN_TEMPLATES if t.id == template_id),
            None
        )
        
        if template is None:
            return None
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "customization_tips": template.customization_tips,
            "default_persona": template.default_persona.model_dump(),
        }
    
    # ─────────────────────────────────────────────────────────────────
    # Stats
    # ─────────────────────────────────────────────────────────────────
    
    async def record_chat_started(self, character_id: str):
        """Record that a chat was started with this character."""
        await self.initialize()
        await self._repo.increment_chat_count(character_id)


# Singleton instance
_character_service: Optional[CharacterService] = None


async def get_character_service() -> CharacterService:
    """Get the character service instance."""
    global _character_service
    if _character_service is None:
        _character_service = CharacterService()
        await _character_service.initialize()
    return _character_service

