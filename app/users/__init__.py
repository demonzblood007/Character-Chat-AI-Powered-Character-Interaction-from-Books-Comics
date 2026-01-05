"""
Users Module
============

This module provides user management functionality including:
- User models and schemas
- User repository (database operations)
- User service (business logic)

Follows SOLID principles with clear separation of concerns.
"""

from .models import User, UserPreferences, UserSubscription, UserStats, AuthProvider, SubscriptionTier
from .schemas import UserCreate, UserUpdate, UserResponse, UserInDB
from .repository import UserRepository
from .service import UserService

__all__ = [
    # Models
    "User",
    "UserPreferences", 
    "UserSubscription",
    "UserStats",
    "AuthProvider",
    "SubscriptionTier",
    # Schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Repository & Service
    "UserRepository",
    "UserService",
]

