"""
User Domain Models
==================

Core domain models for user management.
These models represent the business domain, not the database schema.

Design Principles:
- Immutable where possible (frozen dataclasses)
- Rich domain behavior
- Clear value objects
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass, field
from bson import ObjectId


class AuthProvider(str, Enum):
    """Supported authentication providers."""
    GOOGLE = "google"
    GITHUB = "github"  # Future
    EMAIL = "email"    # Future


class SubscriptionTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


@dataclass
class UserPreferences:
    """User preferences and settings."""
    theme: str = "system"  # system, light, dark
    notifications_enabled: bool = True
    email_notifications: bool = True
    default_chat_mode: str = "casual"  # casual, roleplay, story
    language: str = "en"
    
    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "notifications_enabled": self.notifications_enabled,
            "email_notifications": self.email_notifications,
            "default_chat_mode": self.default_chat_mode,
            "language": self.language,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        if not data:
            return cls()
        return cls(
            theme=data.get("theme", "system"),
            notifications_enabled=data.get("notifications_enabled", True),
            email_notifications=data.get("email_notifications", True),
            default_chat_mode=data.get("default_chat_mode", "casual"),
            language=data.get("language", "en"),
        )


@dataclass
class UserSubscription:
    """User subscription details."""
    tier: SubscriptionTier = SubscriptionTier.FREE
    credits: int = 100  # Free tier starts with 100 credits
    credits_reset_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "credits": self.credits,
            "credits_reset_at": self.credits_reset_at,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserSubscription":
        if not data:
            return cls()
        return cls(
            tier=SubscriptionTier(data.get("tier", "free")),
            credits=data.get("credits", 100),
            credits_reset_at=data.get("credits_reset_at"),
            started_at=data.get("started_at"),
            expires_at=data.get("expires_at"),
        )
    
    def has_credits(self, amount: int = 1) -> bool:
        """Check if user has enough credits."""
        return self.credits >= amount
    
    def deduct_credits(self, amount: int = 1) -> bool:
        """Deduct credits if available. Returns True if successful."""
        if self.has_credits(amount):
            self.credits -= amount
            return True
        return False


@dataclass
class UserStats:
    """User usage statistics."""
    books_uploaded: int = 0
    total_chats: int = 0
    characters_created: int = 0
    stories_created: int = 0
    total_messages_sent: int = 0
    
    def to_dict(self) -> dict:
        return {
            "books_uploaded": self.books_uploaded,
            "total_chats": self.total_chats,
            "characters_created": self.characters_created,
            "stories_created": self.stories_created,
            "total_messages_sent": self.total_messages_sent,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserStats":
        if not data:
            return cls()
        return cls(
            books_uploaded=data.get("books_uploaded", 0),
            total_chats=data.get("total_chats", 0),
            characters_created=data.get("characters_created", 0),
            stories_created=data.get("stories_created", 0),
            total_messages_sent=data.get("total_messages_sent", 0),
        )


@dataclass
class UserAuth:
    """User authentication details."""
    provider: AuthProvider
    provider_id: str
    email_verified: bool = False
    
    def to_dict(self) -> dict:
        return {
            "provider": self.provider.value,
            "provider_id": self.provider_id,
            "email_verified": self.email_verified,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserAuth":
        return cls(
            provider=AuthProvider(data["provider"]),
            provider_id=data["provider_id"],
            email_verified=data.get("email_verified", False),
        )


@dataclass
class User:
    """
    User domain model.
    
    This is the core user entity with all user-related data.
    It's designed to be rich with behavior, not just a data container.
    """
    id: Optional[str] = None
    email: str = ""
    name: str = ""
    avatar_url: Optional[str] = None
    
    # Authentication
    auth: Optional[UserAuth] = None
    
    # Subscription & Credits
    subscription: UserSubscription = field(default_factory=UserSubscription)
    
    # Usage Stats
    stats: UserStats = field(default_factory=UserStats)
    
    # Preferences
    preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamps if not provided."""
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    @property
    def display_name(self) -> str:
        """Get display name, falling back to email if name not set."""
        return self.name or self.email.split("@")[0]
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription."""
        return self.subscription.tier in (SubscriptionTier.PRO, SubscriptionTier.PREMIUM)
    
    def can_upload_book(self) -> bool:
        """Check if user can upload a book based on their tier and limits."""
        limits = {
            SubscriptionTier.FREE: 3,
            SubscriptionTier.PRO: 20,
            SubscriptionTier.PREMIUM: 100,
        }
        max_books = limits.get(self.subscription.tier, 3)
        return self.stats.books_uploaded < max_books
    
    def can_chat(self) -> bool:
        """Check if user can chat (has credits and is active)."""
        return self.is_active and self.subscription.has_credits()
    
    def record_login(self) -> None:
        """Record a login event."""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for database storage."""
        return {
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "auth": self.auth.to_dict() if self.auth else None,
            "subscription": self.subscription.to_dict(),
            "stats": self.stats.to_dict(),
            "preferences": self.preferences.to_dict(),
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create user from dictionary (database document)."""
        user_id = data.get("_id")
        if user_id and isinstance(user_id, ObjectId):
            user_id = str(user_id)
        
        auth_data = data.get("auth")
        auth = UserAuth.from_dict(auth_data) if auth_data else None
        
        return cls(
            id=user_id,
            email=data.get("email", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url"),
            auth=auth,
            subscription=UserSubscription.from_dict(data.get("subscription", {})),
            stats=UserStats.from_dict(data.get("stats", {})),
            preferences=UserPreferences.from_dict(data.get("preferences", {})),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login_at=data.get("last_login_at"),
        )

