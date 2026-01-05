"""
User Pydantic Schemas
=====================

Schemas for API request/response validation.
Separate from domain models to allow different representations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from .models import AuthProvider, SubscriptionTier


# ────────────────────────────────
# Nested Schemas
# ────────────────────────────────

class UserPreferencesSchema(BaseModel):
    """User preferences for API responses."""
    theme: str = "system"
    notifications_enabled: bool = True
    email_notifications: bool = True
    default_chat_mode: str = "casual"
    language: str = "en"


class UserSubscriptionSchema(BaseModel):
    """User subscription for API responses."""
    tier: SubscriptionTier = SubscriptionTier.FREE
    credits: int = 100
    credits_reset_at: Optional[datetime] = None


class UserStatsSchema(BaseModel):
    """User statistics for API responses."""
    books_uploaded: int = 0
    total_chats: int = 0
    characters_created: int = 0
    stories_created: int = 0


class UserAuthSchema(BaseModel):
    """User auth info for API responses."""
    provider: AuthProvider
    email_verified: bool = False


# ────────────────────────────────
# Request Schemas
# ────────────────────────────────

class UserCreate(BaseModel):
    """Schema for creating a new user (internal use)."""
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    auth_provider: AuthProvider
    auth_provider_id: str
    is_verified: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "auth_provider": "google",
                "auth_provider_id": "google-123456",
                "is_verified": True,
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = None
    preferences: Optional[UserPreferencesSchema] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Smith",
                "preferences": {
                    "theme": "dark",
                    "notifications_enabled": True,
                }
            }
        }


class PreferencesUpdate(BaseModel):
    """Schema for updating just preferences."""
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    default_chat_mode: Optional[str] = None
    language: Optional[str] = None


# ────────────────────────────────
# Response Schemas
# ────────────────────────────────

class UserResponse(BaseModel):
    """User data returned to clients (public view)."""
    id: str
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    auth: UserAuthSchema
    subscription: UserSubscriptionSchema
    stats: UserStatsSchema
    preferences: UserPreferencesSchema
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "auth": {
                    "provider": "google",
                    "email_verified": True,
                },
                "subscription": {
                    "tier": "free",
                    "credits": 100,
                },
                "stats": {
                    "books_uploaded": 2,
                    "total_chats": 45,
                },
                "preferences": {
                    "theme": "dark",
                    "notifications_enabled": True,
                },
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-01-15T10:30:00Z",
                "last_login_at": "2024-01-20T14:22:00Z",
            }
        }


class UserInDB(BaseModel):
    """Full user data including internal fields (for internal use)."""
    id: str
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    auth_provider: AuthProvider
    auth_provider_id: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    credits: int = 100
    books_uploaded: int = 0
    total_chats: int = 0
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserPublicProfile(BaseModel):
    """Public profile visible to other users."""
    id: str
    name: str
    avatar_url: Optional[str] = None
    books_uploaded: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

