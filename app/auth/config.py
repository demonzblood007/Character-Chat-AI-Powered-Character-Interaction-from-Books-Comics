"""
Authentication Configuration
============================

Centralized configuration for authentication settings.
All sensitive values are loaded from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache


@dataclass(frozen=True)
class JWTConfig:
    """JWT token configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


@dataclass(frozen=True)
class GoogleOAuthConfig:
    """Google OAuth2 configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple = (
        "openid",
        "email",
        "profile",
    )


@dataclass(frozen=True)
class AuthConfig:
    """Main authentication configuration."""
    jwt: JWTConfig
    google: Optional[GoogleOAuthConfig]
    
    # Cookie settings
    cookie_secure: bool = True  # Set to False for local development
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    cookie_domain: Optional[str] = None


@lru_cache()
def get_auth_config() -> AuthConfig:
    """
    Get authentication configuration from environment.
    Cached for performance.
    """
    # JWT Configuration
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    
    jwt_config = JWTConfig(
        secret_key=jwt_secret,
        algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        refresh_token_expire_days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    )
    
    # Google OAuth Configuration (optional)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    google_config = None
    if google_client_id and google_client_secret:
        google_config = GoogleOAuthConfig(
            client_id=google_client_id,
            client_secret=google_client_secret,
            redirect_uri=google_redirect_uri,
        )
    
    return AuthConfig(
        jwt=jwt_config,
        google=google_config,
        cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true",
        cookie_httponly=True,
        cookie_samesite=os.getenv("AUTH_COOKIE_SAMESITE", "lax"),
        cookie_domain=os.getenv("AUTH_COOKIE_DOMAIN"),
    )

