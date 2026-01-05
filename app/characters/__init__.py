"""
Character Library
=================

Manage characters for conversation - both pre-built and user-created.

Core Philosophy:
- Start simple, get chatting fast
- Pre-built characters for instant gratification
- Easy character creation with templates
- Discovery without overwhelm
"""

from .models import Character, CharacterTemplate, CharacterCategory
from .service import CharacterService
from .router import router as character_router

__all__ = [
    "Character",
    "CharacterTemplate", 
    "CharacterCategory",
    "CharacterService",
    "character_router",
]

