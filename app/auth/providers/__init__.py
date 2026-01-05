"""
OAuth Providers
===============

Abstract and concrete OAuth provider implementations.
Follows Open/Closed principle - new providers can be added without modifying existing code.
"""

from .base import OAuthProvider, OAuthUserInfo, OAuthTokens
from .google import GoogleOAuthProvider

__all__ = [
    "OAuthProvider",
    "OAuthUserInfo",
    "OAuthTokens",
    "GoogleOAuthProvider",
]

