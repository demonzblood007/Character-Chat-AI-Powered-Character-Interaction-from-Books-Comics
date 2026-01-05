"""
OAuth Provider Base
===================

Abstract base class for OAuth providers.
Defines the interface that all OAuth providers must implement.

Open/Closed Principle: 
- This class is closed for modification
- New providers are open for extension
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OAuthUserInfo:
    """
    User information returned by OAuth providers.
    
    This is a provider-agnostic representation of user data.
    Each provider implementation maps their response to this format.
    """
    provider_id: str          # Unique ID from the provider
    email: str                # User's email
    name: str                 # User's display name
    avatar_url: Optional[str] # Profile picture URL
    email_verified: bool      # Whether email is verified by provider
    
    # Raw data for debugging/logging (optional)
    raw_data: Optional[dict] = None


@dataclass
class OAuthTokens:
    """
    Tokens returned by OAuth providers.
    """
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None  # Seconds until expiration
    scope: Optional[str] = None


class OAuthProvider(ABC):
    """
    Abstract base class for OAuth providers.
    
    All OAuth providers (Google, GitHub, Apple, etc.) must implement this interface.
    This allows the auth service to work with any provider without knowing the specifics.
    
    Liskov Substitution: Any implementation can be used wherever OAuthProvider is expected.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the provider name (e.g., 'google', 'github').
        
        Returns:
            Provider identifier string
        """
        ...
    
    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """
        Generate the OAuth authorization URL.
        
        Users are redirected to this URL to authenticate with the provider.
        
        Args:
            state: CSRF protection token (should be validated on callback)
            redirect_uri: Optional override for redirect URI
            
        Returns:
            Full authorization URL with query parameters
        """
        ...
    
    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> OAuthTokens:
        """
        Exchange authorization code for tokens.
        
        Called after user is redirected back from provider with auth code.
        
        Args:
            code: Authorization code from provider
            redirect_uri: Must match the one used in authorization URL
            
        Returns:
            OAuth tokens (access, refresh, etc.)
            
        Raises:
            OAuthError: If code exchange fails
        """
        ...
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Get user information using access token.
        
        Args:
            access_token: Valid access token from provider
            
        Returns:
            User information
            
        Raises:
            OAuthError: If fetching user info fails
        """
        ...
    
    async def authenticate(self, code: str, redirect_uri: Optional[str] = None) -> OAuthUserInfo:
        """
        Complete authentication flow: exchange code and get user info.
        
        Convenience method that combines code exchange and user info fetch.
        
        Args:
            code: Authorization code from provider
            redirect_uri: Must match the one used in authorization URL
            
        Returns:
            User information
        """
        tokens = await self.exchange_code(code, redirect_uri)
        return await self.get_user_info(tokens.access_token)

