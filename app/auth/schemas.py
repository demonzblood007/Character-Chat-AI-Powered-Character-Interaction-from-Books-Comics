"""
Authentication Schemas
======================

Pydantic schemas for authentication request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, Field
from app.users.schemas import UserResponse


# ────────────────────────────────
# OAuth Schemas
# ────────────────────────────────

class OAuthURLResponse(BaseModel):
    """Response containing OAuth authorization URL."""
    authorization_url: str
    state: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
                "state": "random-state-token-for-csrf-protection"
            }
        }


class OAuthCallbackRequest(BaseModel):
    """Request body for OAuth callback."""
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State token for CSRF validation")
    redirect_uri: Optional[str] = Field(None, description="Optional redirect URI override")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "4/0AX4XfWh...",
                "state": "random-state-token",
            }
        }


# ────────────────────────────────
# Token Schemas
# ────────────────────────────────

class TokenResponse(BaseModel):
    """Response containing JWT tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 900
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str = Field(..., description="Valid refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ────────────────────────────────
# Auth Result Schemas
# ────────────────────────────────

class AuthResponse(BaseModel):
    """Response for successful authentication."""
    user: UserResponse
    tokens: TokenResponse
    is_new_user: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "507f1f77bcf86cd799439011",
                    "email": "user@example.com",
                    "name": "John Doe",
                },
                "tokens": {
                    "access_token": "eyJ...",
                    "refresh_token": "eyJ...",
                    "token_type": "Bearer",
                    "expires_in": 900
                },
                "is_new_user": True
            }
        }


class LogoutRequest(BaseModel):
    """Request to logout."""
    refresh_token: Optional[str] = Field(None, description="Optional refresh token to invalidate")


class LogoutResponse(BaseModel):
    """Response for logout."""
    message: str = "Successfully logged out"


# ────────────────────────────────
# Error Schemas
# ────────────────────────────────

class AuthErrorResponse(BaseModel):
    """Standard error response for auth errors."""
    detail: str
    error_code: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid credentials",
                "error_code": "INVALID_CREDENTIALS"
            }
        }

