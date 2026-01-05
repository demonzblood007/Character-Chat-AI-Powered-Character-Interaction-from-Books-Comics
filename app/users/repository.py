"""
User Repository
===============

Data access layer for user operations.
Follows Repository pattern for clean separation of data access logic.

Interface Segregation:
- IUserReader: Read operations only
- IUserWriter: Write operations only
- UserRepository: Full implementation
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from .models import User, UserAuth, AuthProvider
from .exceptions import UserNotFoundError, UserAlreadyExistsError


# ────────────────────────────────
# Interfaces (Interface Segregation)
# ────────────────────────────────

class IUserReader(Protocol):
    """Interface for reading user data."""
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        ...
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        ...
    
    async def get_by_provider(self, provider: AuthProvider, provider_id: str) -> Optional[User]:
        """Get user by OAuth provider and provider ID."""
        ...
    
    async def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        ...


class IUserWriter(Protocol):
    """Interface for writing user data."""
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        ...
    
    async def update(self, user_id: str, data: dict) -> User:
        """Update user by ID."""
        ...
    
    async def delete(self, user_id: str) -> bool:
        """Delete user by ID (soft delete)."""
        ...


class IUserRepository(IUserReader, IUserWriter, Protocol):
    """Full user repository interface."""
    pass


# ────────────────────────────────
# Implementation
# ────────────────────────────────

class UserRepository:
    """
    MongoDB implementation of user repository.
    
    Single Responsibility: Only handles database operations for users.
    Dependency Inversion: Depends on AsyncIOMotorCollection abstraction.
    """
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """
        Initialize repository with MongoDB collection.
        
        Args:
            collection: Motor async collection for users
        """
        self._collection = collection
    
    async def ensure_indexes(self) -> None:
        """Create necessary indexes for the users collection."""
        await self._collection.create_index("email", unique=True)
        await self._collection.create_index(
            [("auth.provider", 1), ("auth.provider_id", 1)],
            unique=True,
            sparse=True  # Allow documents without auth field
        )
        await self._collection.create_index("created_at", background=True)
    
    # ────────────────────────────────
    # Read Operations
    # ────────────────────────────────
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User's ObjectId as string
            
        Returns:
            User if found, None otherwise
        """
        try:
            doc = await self._collection.find_one({"_id": ObjectId(user_id)})
            return User.from_dict(doc) if doc else None
        except Exception:
            return None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User's email address
            
        Returns:
            User if found, None otherwise
        """
        doc = await self._collection.find_one({"email": email.lower()})
        return User.from_dict(doc) if doc else None
    
    async def get_by_provider(self, provider: AuthProvider, provider_id: str) -> Optional[User]:
        """
        Get user by OAuth provider and provider ID.
        
        Args:
            provider: OAuth provider (google, github, etc.)
            provider_id: User ID from the provider
            
        Returns:
            User if found, None otherwise
        """
        doc = await self._collection.find_one({
            "auth.provider": provider.value,
            "auth.provider_id": provider_id
        })
        return User.from_dict(doc) if doc else None
    
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email.
        
        Args:
            email: Email to check
            
        Returns:
            True if user exists
        """
        count = await self._collection.count_documents(
            {"email": email.lower()},
            limit=1
        )
        return count > 0
    
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 20,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """
        List users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            
        Returns:
            List of users
        """
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        
        cursor = self._collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        users = []
        async for doc in cursor:
            users.append(User.from_dict(doc))
        return users
    
    # ────────────────────────────────
    # Write Operations
    # ────────────────────────────────
    
    async def create(self, user: User) -> User:
        """
        Create a new user.
        
        Args:
            user: User to create
            
        Returns:
            Created user with ID
            
        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        # Normalize email to lowercase
        user.email = user.email.lower()
        
        # Check if user already exists
        if await self.exists_by_email(user.email):
            raise UserAlreadyExistsError(f"User with email {user.email} already exists")
        
        # Prepare document
        now = datetime.utcnow()
        doc = user.to_dict()
        doc["created_at"] = now
        doc["updated_at"] = now
        
        # Insert
        result = await self._collection.insert_one(doc)
        user.id = str(result.inserted_id)
        user.created_at = now
        user.updated_at = now
        
        return user
    
    async def update(self, user_id: str, data: dict) -> User:
        """
        Update user by ID.
        
        Args:
            user_id: User ID
            data: Fields to update
            
        Returns:
            Updated user
            
        Raises:
            UserNotFoundError: If user not found
        """
        # Add updated timestamp
        data["updated_at"] = datetime.utcnow()
        
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": data},
            return_document=True
        )
        
        if not result:
            raise UserNotFoundError(f"User {user_id} not found")
        
        return User.from_dict(result)
    
    async def update_stats(self, user_id: str, stat_updates: dict) -> User:
        """
        Increment user statistics.
        
        Args:
            user_id: User ID
            stat_updates: Stats to increment (e.g., {"stats.books_uploaded": 1})
            
        Returns:
            Updated user
        """
        update_doc = {"$inc": stat_updates, "$set": {"updated_at": datetime.utcnow()}}
        
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            update_doc,
            return_document=True
        )
        
        if not result:
            raise UserNotFoundError(f"User {user_id} not found")
        
        return User.from_dict(result)
    
    async def update_credits(self, user_id: str, amount: int) -> User:
        """
        Update user credits (can be positive or negative).
        
        Args:
            user_id: User ID
            amount: Amount to add (or subtract if negative)
            
        Returns:
            Updated user
        """
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {"subscription.credits": amount},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=True
        )
        
        if not result:
            raise UserNotFoundError(f"User {user_id} not found")
        
        return User.from_dict(result)
    
    async def record_login(self, user_id: str) -> User:
        """
        Record a login event for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user
        """
        now = datetime.utcnow()
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login_at": now, "updated_at": now}},
            return_document=True
        )
        
        if not result:
            raise UserNotFoundError(f"User {user_id} not found")
        
        return User.from_dict(result)
    
    async def delete(self, user_id: str) -> bool:
        """
        Soft delete user by setting is_active to False.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted
        """
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    async def hard_delete(self, user_id: str) -> bool:
        """
        Permanently delete user (use with caution).
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted
        """
        result = await self._collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0
    
    # ────────────────────────────────
    # Upsert Operations
    # ────────────────────────────────
    
    async def upsert_by_provider(
        self,
        provider: AuthProvider,
        provider_id: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
        email_verified: bool = False
    ) -> tuple[User, bool]:
        """
        Create or update user by OAuth provider.
        Used during OAuth login flow.
        
        Args:
            provider: OAuth provider
            provider_id: User ID from provider
            email: User's email
            name: User's name
            avatar_url: User's avatar URL
            email_verified: Whether email is verified by provider
            
        Returns:
            Tuple of (User, is_new_user)
        """
        now = datetime.utcnow()
        
        # Try to find existing user by provider
        existing = await self.get_by_provider(provider, provider_id)
        
        if existing:
            # Update existing user
            updated = await self.update(existing.id, {
                "name": name,
                "avatar_url": avatar_url,
                "auth.email_verified": email_verified,
                "last_login_at": now,
            })
            return updated, False
        
        # Check if user exists by email (might have signed up with different provider)
        existing_by_email = await self.get_by_email(email)
        
        if existing_by_email:
            # Link this provider to existing account
            # Note: In production, you might want to verify ownership first
            updated = await self.update(existing_by_email.id, {
                "auth": {
                    "provider": provider.value,
                    "provider_id": provider_id,
                    "email_verified": email_verified,
                },
                "name": name or existing_by_email.name,
                "avatar_url": avatar_url or existing_by_email.avatar_url,
                "last_login_at": now,
            })
            return updated, False
        
        # Create new user
        new_user = User(
            email=email.lower(),
            name=name,
            avatar_url=avatar_url,
            auth=UserAuth(
                provider=provider,
                provider_id=provider_id,
                email_verified=email_verified,
            ),
            is_verified=email_verified,
            last_login_at=now,
        )
        
        created = await self.create(new_user)
        return created, True

