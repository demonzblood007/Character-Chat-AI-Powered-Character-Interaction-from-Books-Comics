"""
User Service
============

Business logic layer for user operations.
Orchestrates repository calls and applies business rules.

Single Responsibility: Contains only user-related business logic.
Dependency Inversion: Depends on repository abstraction, not implementation.
"""

from typing import Optional, List
from datetime import datetime

from .models import User, AuthProvider, SubscriptionTier
from .repository import UserRepository
from .schemas import UserUpdate, PreferencesUpdate
from .exceptions import (
    UserNotFoundError,
    UserDeactivatedError,
    InsufficientCreditsError,
    BookLimitReachedError,
)


class UserService:
    """
    User service for business logic.
    
    This service layer:
    - Applies business rules
    - Orchestrates repository calls
    - Validates operations
    """
    
    def __init__(self, repository: UserRepository):
        """
        Initialize service with repository.
        
        Args:
            repository: User repository for data access
        """
        self._repo = repository
    
    # ────────────────────────────────
    # Read Operations
    # ────────────────────────────────
    
    async def get_user(self, user_id: str) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User
            
        Raises:
            UserNotFoundError: If user not found
            UserDeactivatedError: If user is deactivated
        """
        user = await self._repo.get_by_id(user_id)
        
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        
        if not user.is_active:
            raise UserDeactivatedError("This account has been deactivated")
        
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User or None
        """
        return await self._repo.get_by_email(email)
    
    async def get_active_user(self, user_id: str) -> User:
        """
        Get user by ID, ensuring they are active.
        
        Args:
            user_id: User ID
            
        Returns:
            Active user
            
        Raises:
            UserNotFoundError: If user not found
            UserDeactivatedError: If user is deactivated
        """
        user = await self.get_user(user_id)
        
        if not user.is_active:
            raise UserDeactivatedError("This account has been deactivated")
        
        return user
    
    # ────────────────────────────────
    # Update Operations
    # ────────────────────────────────
    
    async def update_profile(self, user_id: str, update: UserUpdate) -> User:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            update: Profile updates
            
        Returns:
            Updated user
        """
        # Build update dict, excluding None values
        update_data = {}
        
        if update.name is not None:
            update_data["name"] = update.name
        
        if update.avatar_url is not None:
            update_data["avatar_url"] = update.avatar_url
        
        if update.preferences is not None:
            update_data["preferences"] = update.preferences.model_dump()
        
        if not update_data:
            return await self.get_user(user_id)
        
        return await self._repo.update(user_id, update_data)
    
    async def update_preferences(self, user_id: str, update: PreferencesUpdate) -> User:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            update: Preferences updates
            
        Returns:
            Updated user
        """
        # Get current user to merge preferences
        user = await self.get_user(user_id)
        
        # Build update dict
        prefs = user.preferences.to_dict()
        
        if update.theme is not None:
            prefs["theme"] = update.theme
        if update.notifications_enabled is not None:
            prefs["notifications_enabled"] = update.notifications_enabled
        if update.email_notifications is not None:
            prefs["email_notifications"] = update.email_notifications
        if update.default_chat_mode is not None:
            prefs["default_chat_mode"] = update.default_chat_mode
        if update.language is not None:
            prefs["language"] = update.language
        
        return await self._repo.update(user_id, {"preferences": prefs})
    
    # ────────────────────────────────
    # Credit Operations
    # ────────────────────────────────
    
    async def check_and_deduct_credits(self, user_id: str, amount: int = 1) -> User:
        """
        Check if user has credits and deduct them.
        
        Args:
            user_id: User ID
            amount: Credits to deduct
            
        Returns:
            Updated user
            
        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        user = await self.get_user(user_id)
        
        if not user.subscription.has_credits(amount):
            raise InsufficientCreditsError(
                f"Insufficient credits. Required: {amount}, Available: {user.subscription.credits}"
            )
        
        return await self._repo.update_credits(user_id, -amount)
    
    async def add_credits(self, user_id: str, amount: int) -> User:
        """
        Add credits to user account.
        
        Args:
            user_id: User ID
            amount: Credits to add
            
        Returns:
            Updated user
        """
        return await self._repo.update_credits(user_id, amount)
    
    # ────────────────────────────────
    # Subscription Operations
    # ────────────────────────────────
    
    async def upgrade_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier,
        credits: int = 0
    ) -> User:
        """
        Upgrade user subscription.
        
        Args:
            user_id: User ID
            tier: New subscription tier
            credits: Additional credits to add
            
        Returns:
            Updated user
        """
        now = datetime.utcnow()
        
        return await self._repo.update(user_id, {
            "subscription.tier": tier.value,
            "subscription.credits": credits,
            "subscription.started_at": now,
        })
    
    # ────────────────────────────────
    # Usage Tracking
    # ────────────────────────────────
    
    async def record_book_upload(self, user_id: str) -> User:
        """
        Record a book upload, checking limits.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user
            
        Raises:
            BookLimitReachedError: If user has reached upload limit
        """
        user = await self.get_user(user_id)
        
        if not user.can_upload_book():
            raise BookLimitReachedError(
                f"You have reached the book limit ({user.stats.books_uploaded}) for your subscription tier. "
                "Please upgrade to upload more books."
            )
        
        return await self._repo.update_stats(user_id, {"stats.books_uploaded": 1})
    
    async def record_chat(self, user_id: str) -> User:
        """
        Record a chat interaction.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user
        """
        return await self._repo.update_stats(user_id, {
            "stats.total_chats": 1,
            "stats.total_messages_sent": 1,
        })
    
    async def record_character_created(self, user_id: str) -> User:
        """
        Record a character creation.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user
        """
        return await self._repo.update_stats(user_id, {"stats.characters_created": 1})
    
    # ────────────────────────────────
    # Account Management
    # ────────────────────────────────
    
    async def deactivate_account(self, user_id: str) -> bool:
        """
        Deactivate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deactivated
        """
        return await self._repo.delete(user_id)
    
    async def reactivate_account(self, user_id: str) -> User:
        """
        Reactivate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            Reactivated user
        """
        return await self._repo.update(user_id, {"is_active": True})

