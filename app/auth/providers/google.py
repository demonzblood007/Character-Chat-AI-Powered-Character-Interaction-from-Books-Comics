"""
Google OAuth Provider
=====================

Implementation of OAuth provider for Google Sign-In.

Uses Google's OAuth 2.0 API:
- Authorization: https://accounts.google.com/o/oauth2/v2/auth
- Token exchange: https://oauth2.googleapis.com/token
- User info: https://www.googleapis.com/oauth2/v2/userinfo
"""

import httpx
from typing import Optional
from urllib.parse import urlencode

from .base import OAuthProvider, OAuthUserInfo, OAuthTokens
from ..exceptions import OAuthError, OAuthProviderNotConfiguredError
from ..config import GoogleOAuthConfig


class GoogleOAuthProvider(OAuthProvider):
    """
    Google OAuth 2.0 provider implementation.
    
    Handles:
    - Authorization URL generation
    - Code exchange for tokens
    - User info retrieval
    """
    
    # Google OAuth endpoints
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self, config: GoogleOAuthConfig):
        """
        Initialize Google OAuth provider.
        
        Args:
            config: Google OAuth configuration
            
        Raises:
            OAuthProviderNotConfiguredError: If config is None
        """
        if not config:
            raise OAuthProviderNotConfiguredError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        
        self._config = config
        self._client = httpx.AsyncClient(timeout=10.0)
    
    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "google"
    
    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: CSRF protection token
            redirect_uri: Optional override for redirect URI
            
        Returns:
            Full authorization URL
        """
        params = {
            "client_id": self._config.client_id,
            "redirect_uri": redirect_uri or self._config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._config.scopes),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "select_account",  # Always show account picker
        }
        
        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
    
    async def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> OAuthTokens:
        """
        Exchange authorization code for Google tokens.
        
        Args:
            code: Authorization code from Google
            redirect_uri: Must match the one used in authorization
            
        Returns:
            OAuth tokens
            
        Raises:
            OAuthError: If exchange fails
        """
        try:
            response = await self._client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri or self._config.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise OAuthError(f"Google token exchange failed: {error_msg}")
            
            data = response.json()
            
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
            )
            
        except httpx.RequestError as e:
            raise OAuthError(f"Network error during Google authentication: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Get user information from Google.
        
        Args:
            access_token: Valid Google access token
            
        Returns:
            User information
            
        Raises:
            OAuthError: If fetching user info fails
        """
        try:
            response = await self._client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                raise OAuthError(f"Failed to get Google user info: {response.text}")
            
            data = response.json()
            
            return OAuthUserInfo(
                provider_id=data["id"],
                email=data["email"],
                name=data.get("name", data.get("email", "").split("@")[0]),
                avatar_url=data.get("picture"),
                email_verified=data.get("verified_email", False),
                raw_data=data,
            )
            
        except httpx.RequestError as e:
            raise OAuthError(f"Network error fetching Google user info: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """
        Refresh Google access token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New OAuth tokens
            
        Raises:
            OAuthError: If refresh fails
        """
        try:
            response = await self._client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise OAuthError(f"Google token refresh failed: {error_msg}")
            
            data = response.json()
            
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),  # May not return new refresh token
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
            )
            
        except httpx.RequestError as e:
            raise OAuthError(f"Network error during Google token refresh: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

