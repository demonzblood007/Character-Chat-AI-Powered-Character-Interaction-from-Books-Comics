"""
Character Library Router
========================

Clean, user-friendly API for the character library.

Endpoints designed for:
- Quick discovery (browse, search)
- Easy creation (templates + custom)
- Personal collections (favorites, my characters)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Path
from typing import List, Optional

from .schemas import (
    CreateCharacterRequest,
    CreateFromTemplateRequest,
    UpdateCharacterRequest,
    CharacterCard,
    CharacterDetail,
    CharacterListResponse,
    FeaturedResponse,
    CategoryInfo,
    TemplateInfo,
    TemplateDetail,
)
from .models import CharacterPersona, CharacterCategory, CharacterVisibility
from .service import get_character_service, CharacterService

# Import auth
from app.auth import get_current_user_optional
from app.users.models import User


router = APIRouter(prefix="/characters", tags=["Character Library"])


async def get_user_id(
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> str:
    """Get user ID from auth or header."""
    if current_user:
        return current_user.id
    if x_user_id:
        return x_user_id
    raise HTTPException(status_code=401, detail="Authentication required")


async def get_optional_user_id(
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> Optional[str]:
    """Get user ID if available (for anonymous browsing)."""
    if current_user:
        return current_user.id
    return x_user_id


# ─────────────────────────────────────────────────────────────────
# Discovery (Public)
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/featured",
    response_model=FeaturedResponse,
    summary="Get featured characters",
    description="Get curated characters for homepage. No auth required.",
)
async def get_featured(
    service: CharacterService = Depends(get_character_service),
):
    """Get featured characters for homepage."""
    return await service.get_featured_characters()


@router.get(
    "/search",
    response_model=CharacterListResponse,
    summary="Search characters",
    description="Search public characters by name, tags, or source material.",
)
async def search_characters(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    official: bool = Query(False, description="Only official characters"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    service: CharacterService = Depends(get_character_service),
):
    """Search the character library."""
    result = await service.search_characters(
        query=q,
        category=category,
        official_only=official,
        page=page,
        page_size=page_size,
    )
    return CharacterListResponse(**result)


@router.get(
    "/categories",
    response_model=List[CategoryInfo],
    summary="Get all categories",
    description="Get available categories with character counts.",
)
async def get_categories(
    service: CharacterService = Depends(get_character_service),
):
    """Get all categories."""
    categories = await service.get_all_categories()
    return [CategoryInfo(**c) for c in categories]


@router.get(
    "/category/{category_id}",
    response_model=CharacterListResponse,
    summary="Get characters by category",
)
async def get_by_category(
    category_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    service: CharacterService = Depends(get_character_service),
):
    """Get characters in a specific category."""
    result = await service.search_characters(
        category=category_id,
        page=page,
        page_size=page_size,
    )
    return CharacterListResponse(**result)


# ─────────────────────────────────────────────────────────────────
# Character Details
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{character_id}",
    response_model=CharacterDetail,
    summary="Get character details",
)
async def get_character(
    character_id: str = Path(..., pattern="^[0-9a-fA-F]{24}$"),
    user_id: Optional[str] = Depends(get_optional_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Get full character details."""
    character = await service.get_character(character_id, user_id or "anonymous")
    
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Build response
    is_favorite = False
    if user_id:
        is_favorite = await service._repo.is_favorite(user_id, character_id)
    
    return CharacterDetail(
        id=character.id,
        name=character.name,
        tagline=character.tagline,
        avatar_url=character.get_avatar_url(),
        category=character.category,
        tags=character.tags,
        source=character.source,
        author=character.author,
        creator_id=character.creator_id,
        visibility=character.visibility,
        is_official=character.is_official,
        chat_count=character.chat_count,
        favorite_count=character.favorite_count,
        persona=character.persona.model_dump(),
        created_at=character.created_at.isoformat(),
        is_favorite=is_favorite,
        is_mine=character.creator_id == user_id,
    )


# ─────────────────────────────────────────────────────────────────
# User Collections
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/me/created",
    response_model=List[CharacterCard],
    summary="Get my characters",
    description="Get characters you've created.",
)
async def get_my_characters(
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Get characters created by current user."""
    characters = await service.get_my_characters(user_id)
    return [CharacterCard(**c) for c in characters]


@router.get(
    "/me/favorites",
    response_model=List[CharacterCard],
    summary="Get my favorites",
    description="Get your favorite characters.",
)
async def get_my_favorites(
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Get user's favorite characters."""
    characters = await service.get_my_favorites(user_id)
    return [CharacterCard(**c) for c in characters]


@router.post(
    "/{character_id}/favorite",
    summary="Add to favorites",
)
async def add_favorite(
    character_id: str,
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Add character to favorites."""
    success = await service.add_to_favorites(user_id, character_id)
    return {"success": success, "message": "Added to favorites" if success else "Already in favorites"}


@router.delete(
    "/{character_id}/favorite",
    summary="Remove from favorites",
)
async def remove_favorite(
    character_id: str,
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Remove character from favorites."""
    success = await service.remove_from_favorites(user_id, character_id)
    return {"success": success}


# ─────────────────────────────────────────────────────────────────
# Character Creation
# ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CharacterDetail,
    summary="Create a character",
    description="Create a new character from scratch.",
)
async def create_character(
    request: CreateCharacterRequest,
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Create a new character."""
    try:
        category = CharacterCategory(request.category)
    except ValueError:
        category = CharacterCategory.ORIGINAL
    
    try:
        visibility = CharacterVisibility(request.visibility)
    except ValueError:
        visibility = CharacterVisibility.PRIVATE
    
    persona = CharacterPersona(**request.persona.model_dump())
    
    character = await service.create_character(
        user_id=user_id,
        name=request.name,
        tagline=request.tagline,
        persona=persona,
        category=category,
        tags=request.tags,
        source=request.source,
        author=request.author,
        visibility=visibility,
        avatar_url=request.avatar_url,
    )
    
    return CharacterDetail(
        id=character.id,
        name=character.name,
        tagline=character.tagline,
        avatar_url=character.get_avatar_url(),
        category=character.category,
        tags=character.tags,
        source=character.source,
        author=character.author,
        creator_id=character.creator_id,
        visibility=character.visibility,
        is_official=character.is_official,
        chat_count=character.chat_count,
        favorite_count=character.favorite_count,
        persona=character.persona.model_dump(),
        created_at=character.created_at.isoformat(),
        is_favorite=False,
        is_mine=True,
    )


@router.post(
    "/from-template",
    response_model=CharacterDetail,
    summary="Create from template",
    description="Create a character based on a template.",
)
async def create_from_template(
    request: CreateFromTemplateRequest,
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Create character from a template."""
    try:
        character = await service.create_from_template(
            user_id=user_id,
            template_id=request.template_id,
            name=request.name,
            tagline=request.tagline,
            customizations=request.customizations,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return CharacterDetail(
        id=character.id,
        name=character.name,
        tagline=character.tagline,
        avatar_url=character.get_avatar_url(),
        category=character.category,
        tags=character.tags,
        source=character.source,
        author=character.author,
        creator_id=character.creator_id,
        visibility=character.visibility,
        is_official=character.is_official,
        chat_count=character.chat_count,
        favorite_count=character.favorite_count,
        persona=character.persona.model_dump(),
        created_at=character.created_at.isoformat(),
        is_favorite=False,
        is_mine=True,
    )


# ─────────────────────────────────────────────────────────────────
# Templates
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/templates/list",
    response_model=List[TemplateInfo],
    summary="Get character templates",
    description="Get available templates for easy character creation.",
)
async def get_templates(
    service: CharacterService = Depends(get_character_service),
):
    """Get all templates."""
    templates = service.get_templates()
    return [TemplateInfo(**t) for t in templates]


@router.get(
    "/templates/{template_id}",
    response_model=TemplateDetail,
    summary="Get template details",
)
async def get_template(
    template_id: str,
    service: CharacterService = Depends(get_character_service),
):
    """Get full template with default values."""
    template = service.get_template(template_id)
    
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateDetail(**template)


# ─────────────────────────────────────────────────────────────────
# Character Management
# ─────────────────────────────────────────────────────────────────

@router.patch(
    "/{character_id}",
    response_model=CharacterDetail,
    summary="Update character",
    description="Update your character's details.",
)
async def update_character(
    character_id: str,
    request: UpdateCharacterRequest,
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Update a character."""
    try:
        updates = request.model_dump(exclude_unset=True)
        
        # Convert persona if present
        if "persona" in updates and updates["persona"]:
            updates["persona"] = updates["persona"]
        
        character = await service.update_character(user_id, character_id, updates)
        
        if character is None:
            raise HTTPException(status_code=404, detail="Character not found")
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    return CharacterDetail(
        id=character.id,
        name=character.name,
        tagline=character.tagline,
        avatar_url=character.get_avatar_url(),
        category=character.category,
        tags=character.tags,
        source=character.source,
        author=character.author,
        creator_id=character.creator_id,
        visibility=character.visibility,
        is_official=character.is_official,
        chat_count=character.chat_count,
        favorite_count=character.favorite_count,
        persona=character.persona.model_dump(),
        created_at=character.created_at.isoformat(),
        is_favorite=False,
        is_mine=True,
    )


@router.delete(
    "/{character_id}",
    summary="Delete character",
    description="Delete a character you created.",
)
async def delete_character(
    character_id: str,
    user_id: str = Depends(get_user_id),
    service: CharacterService = Depends(get_character_service),
):
    """Delete a character."""
    success = await service.delete_character(user_id, character_id)
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail="Character not found or you don't have permission to delete it"
        )
    
    return {"success": True, "message": "Character deleted"}

