"""
Authentication Service
======================

Main authentication service that orchestrates OAuth, tokens, and user management.

Dependency Inversion: Depends on abstractions (interfaces), not implementations.
Single Responsibility: Orchestrates authentication flow only.
"""

import secrets
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from ..config import AuthConfig
from ..providers.base import OAuthProvider, OAuthUserInfo
from ..providers.google import GoogleOAuthProvider
from ..exceptions import (
    OAuthError,
    OAuthProviderNotConfiguredError,
    InvalidTokenError,
    UserNotFoundError,
    UserDeactivatedError,
)
from .token_service import TokenService, TokenPair, TokenPayload, TokenType

from app.users.models import User, AuthProvider
from app.users.repository import UserRepository


@dataclass
class AuthResult:
    """Result of successful authentication."""
    user: User
    tokens: TokenPair
    is_new_user: bool = False


class AuthService:
    """
    Main authentication service.
    
    Orchestrates:
    - OAuth provider authentication
    - Token creation and validation
    - User creation/lookup
    - Session management
    """
    
    def __init__(
        self,
        config: AuthConfig,
        user_repository: UserRepository,
        token_service: Optional[TokenService] = None,
    ):
        """
        Initialize authentication service.
        
        Args:
            config: Authentication configuration
            user_repository: User data access
            token_service: JWT token service (created if not provided)
        """
        self._config = config
        self._user_repo = user_repository
        self._token_service = token_service or TokenService(config.jwt)
        
        # Initialize OAuth providers
        self._providers: Dict[str, OAuthProvider] = {}
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize configured OAuth providers."""
        if self._config.google:
            self._providers["google"] = GoogleOAuthProvider(self._config.google)
    
    def get_provider(self, provider_name: str) -> OAuthProvider:
        """
        Get OAuth provider by name.
        
        Args:
            provider_name: Provider identifier (google, github, etc.)
            
        Returns:
            OAuth provider instance
            
        Raises:
            OAuthProviderNotConfiguredError: If provider not configured
        """
        provider = self._providers.get(provider_name.lower())
        if not provider:
            raise OAuthProviderNotConfiguredError(
                f"OAuth provider '{provider_name}' is not configured"
            )
        return provider
    
    def generate_state(self) -> str:
        """
        Generate a secure state token for OAuth CSRF protection.
        
        Returns:
            Random state string
        """
        return secrets.token_urlsafe(32)
    
    # ────────────────────────────────
    # OAuth Flow
    # ────────────────────────────────
    
    def get_oauth_authorization_url(
        self,
        provider_name: str,
        state: str,
        redirect_uri: Optional[str] = None
    ) -> str:
        """
        Get OAuth authorization URL for a provider.
        
        Args:
            provider_name: OAuth provider name
            state: CSRF state token
            redirect_uri: Optional redirect URI override
            
        Returns:
            Authorization URL
        """
        provider = self.get_provider(provider_name)
        return provider.get_authorization_url(state, redirect_uri)
    
    async def authenticate_oauth(
        self,
        provider_name: str,
        code: str,
        redirect_uri: Optional[str] = None
    ) -> AuthResult:
        """
        Complete OAuth authentication flow.
        
        Args:
            provider_name: OAuth provider name
            code: Authorization code from provider
            redirect_uri: Redirect URI (must match authorization request)
            
        Returns:
            Authentication result with user and tokens
            
        Raises:
            OAuthError: If authentication fails
        """
        # Get provider and authenticate
        provider = self.get_provider(provider_name)
        user_info = await provider.authenticate(code, redirect_uri)
        
        # Map provider name to AuthProvider enum
        auth_provider = AuthProvider(provider_name.lower())
        
        # Create or update user
        user, is_new = await self._user_repo.upsert_by_provider(
            provider=auth_provider,
            provider_id=user_info.provider_id,
            email=user_info.email,
            name=user_info.name,
            avatar_url=user_info.avatar_url,
            email_verified=user_info.email_verified,
        )
        
        # Generate tokens
        tokens = self._token_service.create_token_pair(
            user_id=user.id,
            additional_claims={
                "email": user.email,
                "name": user.name,
            }
        )
        
        return AuthResult(
            user=user,
            tokens=tokens,
            is_new_user=is_new,
        )
    
    # ────────────────────────────────
    # Token Operations
    # ────────────────────────────────
    
    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token pair
            
        Raises:
            InvalidTokenError: If refresh token is invalid
            UserNotFoundError: If user no longer exists
            UserDeactivatedError: If user is deactivated
        """
        # Verify refresh token
        payload = self._token_service.verify_refresh_token(refresh_token)
        
        # Get user to verify they still exist and are active
        user = await self._user_repo.get_by_id(payload.user_id)
        
        if not user:
            raise UserNotFoundError("User not found")
        
        if not user.is_active:
            raise UserDeactivatedError("User account is deactivated")
        
        # Generate new tokens
        return self._token_service.create_token_pair(
            user_id=user.id,
            additional_claims={
                "email": user.email,
                "name": user.name,
            }
        )
    
    def verify_access_token(self, token: str) -> TokenPayload:
        """
        Verify an access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Token payload with user ID
        """
        return self._token_service.verify_access_token(token)
    
    # ────────────────────────────────
    # User Operations
    # ────────────────────────────────
    
    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Current user
            
        Raises:
            InvalidTokenError: If token is invalid
            UserNotFoundError: If user not found
            UserDeactivatedError: If user is deactivated
        """
        payload = self._token_service.verify_access_token(token)
        
        user = await self._user_repo.get_by_id(payload.user_id)
        
        if not user:
            raise UserNotFoundError("User not found")
        
        if not user.is_active:
            raise UserDeactivatedError("User account is deactivated")
        
        return user
    
    # ────────────────────────────────
    # Session Management
    # ────────────────────────────────
    
    async def logout(self, user_id: str, token: Optional[str] = None) -> bool:
        """
        Logout user.
        
        In a production system, this would:
        - Add token to blacklist (Redis)
        - Invalidate all sessions
        - Clear cookies
        
        Args:
            user_id: User ID
            token: Optional token to blacklist
            
        Returns:
            True if successful
        """
        # TODO: Implement token blacklisting with Redis
        # For now, just return True (client should discard tokens)
        return True
    
    async def close(self):
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, 'close'):
                await provider.close()

