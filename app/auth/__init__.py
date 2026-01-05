"""
Authentication Module
=====================

This module provides authentication functionality including:
- OAuth2 providers (Google, extensible to others)
- JWT token management
- User session handling

SOLID Principles Applied:
- Single Responsibility: Each class has one job
- Open/Closed: Abstract providers allow extension without modification
- Liskov Substitution: Any provider can substitute another
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Services depend on abstractions
"""

from .router import router as auth_router
from .dependencies import get_current_user, get_current_user_optional
from .services.token_service import TokenService
from .services.auth_service import AuthService

__all__ = [
    "auth_router",
    "get_current_user",
    "get_current_user_optional",
    "TokenService",
    "AuthService",
]

