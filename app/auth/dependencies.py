"""
Authentication Dependencies
============================

FastAPI dependencies for authentication.
These are injected into route handlers to provide authentication functionality.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_auth_config, AuthConfig
from .services.auth_service import AuthService
from .services.token_service import TokenService
from .exceptions import (
    AuthException,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
    UserDeactivatedError,
)

from app.users.models import User
from app.users.repository import UserRepository
from app.db.client import get_async_database


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


# ────────────────────────────────
# Dependency Providers
# ────────────────────────────────

async def get_user_repository() -> UserRepository:
    """
    Get user repository instance.
    
    Returns:
        UserRepository instance connected to MongoDB
    """
    db = get_async_database()
    return UserRepository(db["users"])


async def get_auth_service(
    config: AuthConfig = Depends(get_auth_config),
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """
    Get authentication service instance.
    
    Args:
        config: Auth configuration
        user_repo: User repository
        
    Returns:
        AuthService instance
    """
    return AuthService(config, user_repo)


async def get_token_service(
    config: AuthConfig = Depends(get_auth_config),
) -> TokenService:
    """
    Get token service instance.
    
    Args:
        config: Auth configuration
        
    Returns:
        TokenService instance
    """
    return TokenService(config.jwt)


# ────────────────────────────────
# Authentication Dependencies
# ────────────────────────────────

def extract_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None, alias="access_token"),
) -> Optional[str]:
    """
    Extract JWT token from Authorization header or cookie.
    
    Priority:
    1. Authorization: Bearer <token> header
    2. access_token cookie
    
    Args:
        credentials: HTTP Bearer credentials from header
        access_token: Token from cookie
        
    Returns:
        Token string or None
    """
    if credentials:
        return credentials.credentials
    return access_token


async def get_current_user(
    token: Optional[str] = Depends(extract_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Get currently authenticated user.
    
    This dependency:
    1. Extracts JWT from header or cookie
    2. Validates the token
    3. Fetches and returns the user
    
    Use this for protected routes that REQUIRE authentication.
    
    Args:
        token: JWT access token
        auth_service: Auth service instance
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if deactivated
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await auth_service.get_current_user(token)
        return user
    
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UserDeactivatedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )


async def get_current_user_optional(
    token: Optional[str] = Depends(extract_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """
    Get currently authenticated user, or None if not authenticated.
    
    Use this for routes that work with or without authentication
    but may provide different behavior for authenticated users.
    
    Args:
        token: JWT access token (optional)
        auth_service: Auth service instance
        
    Returns:
        User if authenticated, None otherwise
    """
    if not token:
        return None
    
    try:
        return await auth_service.get_current_user(token)
    except AuthException:
        return None


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get current user, ensuring they are active.
    
    Args:
        user: Current authenticated user
        
    Returns:
        Active user
        
    Raises:
        HTTPException: 403 if user is not active
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


async def get_current_verified_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user, ensuring they are verified.
    
    Args:
        user: Current active user
        
    Returns:
        Verified user
        
    Raises:
        HTTPException: 403 if user is not verified
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return user


# ────────────────────────────────
# Utility Functions
# ────────────────────────────────

def get_user_id_from_user(user: User = Depends(get_current_user)) -> str:
    """
    Get just the user ID from authenticated user.
    
    Useful for endpoints that only need the user ID, not the full user object.
    
    Args:
        user: Current authenticated user
        
    Returns:
        User ID string
    """
    return user.id

