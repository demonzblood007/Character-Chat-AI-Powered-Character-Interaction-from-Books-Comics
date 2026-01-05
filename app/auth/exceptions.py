"""
Authentication Exceptions
=========================

Custom exceptions for authentication-related errors.
Each exception maps to a specific HTTP status code.
"""

from typing import Optional


class AuthException(Exception):
    """Base exception for authentication errors."""
    status_code: int = 401
    detail: str = "Authentication error"
    
    def __init__(self, detail: Optional[str] = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class InvalidCredentialsError(AuthException):
    """Raised when credentials are invalid."""
    status_code = 401
    detail = "Invalid credentials"


class TokenExpiredError(AuthException):
    """Raised when a token has expired."""
    status_code = 401
    detail = "Token has expired"


class InvalidTokenError(AuthException):
    """Raised when a token is malformed or invalid."""
    status_code = 401
    detail = "Invalid token"


class TokenBlacklistedError(AuthException):
    """Raised when a token has been blacklisted (logged out)."""
    status_code = 401
    detail = "Token has been revoked"


class OAuthError(AuthException):
    """Raised when OAuth flow fails."""
    status_code = 400
    detail = "OAuth authentication failed"


class OAuthProviderNotConfiguredError(AuthException):
    """Raised when an OAuth provider is not configured."""
    status_code = 501
    detail = "OAuth provider not configured"


class UserNotFoundError(AuthException):
    """Raised when a user is not found."""
    status_code = 404
    detail = "User not found"


class UserDeactivatedError(AuthException):
    """Raised when a user account is deactivated."""
    status_code = 403
    detail = "User account is deactivated"


class InsufficientPermissionsError(AuthException):
    """Raised when user lacks required permissions."""
    status_code = 403
    detail = "Insufficient permissions"

