"""
Authentication Router
=====================

FastAPI router for authentication endpoints.

Endpoints:
- GET  /auth/google/url      - Get Google OAuth URL
- POST /auth/google/callback - Handle Google OAuth callback
- POST /auth/refresh         - Refresh access token
- POST /auth/logout          - Logout user
- GET  /auth/me              - Get current user
- PATCH /auth/me             - Update current user profile
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from fastapi.responses import RedirectResponse

from .config import get_auth_config, AuthConfig
from .dependencies import (
    get_auth_service,
    get_current_user,
    get_user_repository,
)
from .services.auth_service import AuthService
from .schemas import (
    OAuthURLResponse,
    OAuthCallbackRequest,
    TokenResponse,
    RefreshTokenRequest,
    AuthResponse,
    LogoutRequest,
    LogoutResponse,
)
from .exceptions import (
    OAuthError,
    OAuthProviderNotConfiguredError,
    InvalidTokenError,
    TokenExpiredError,
)

from app.users.models import User
from app.users.schemas import UserResponse, UserUpdate
from app.users.repository import UserRepository
from app.users.service import UserService


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ────────────────────────────────
# OAuth Endpoints
# ────────────────────────────────

@router.get("/google/url", response_model=OAuthURLResponse)
async def get_google_auth_url(
    redirect_uri: Optional[str] = Query(None, description="Optional redirect URI override"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get Google OAuth authorization URL.
    
    Returns a URL that the client should redirect the user to for Google Sign-In.
    The state token should be stored (e.g., in session) for CSRF validation.
    """
    try:
        state = auth_service.generate_state()
        url = auth_service.get_oauth_authorization_url("google", state, redirect_uri)
        
        return OAuthURLResponse(
            authorization_url=url,
            state=state,
        )
    except OAuthProviderNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )


@router.post("/google/callback", response_model=AuthResponse)
async def google_oauth_callback(
    request: OAuthCallbackRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    config: AuthConfig = Depends(get_auth_config),
):
    """
    Handle Google OAuth callback.
    
    Exchanges the authorization code for tokens and creates/updates the user.
    Returns JWT tokens for the authenticated user.
    
    The client should:
    1. Validate the state token matches what was stored
    2. Store the access token for API requests
    3. Store the refresh token for token refresh
    """
    try:
        # Authenticate with Google
        result = await auth_service.authenticate_oauth(
            provider_name="google",
            code=request.code,
            redirect_uri=request.redirect_uri,
        )
        
        # Set refresh token in httpOnly cookie (more secure)
        response.set_cookie(
            key="refresh_token",
            value=result.tokens.refresh_token,
            httponly=config.cookie_httponly,
            secure=config.cookie_secure,
            samesite=config.cookie_samesite,
            max_age=config.jwt.refresh_token_expire_days * 24 * 60 * 60,
            path="/auth",  # Only sent to auth endpoints
        )
        
        # Build response
        user_response = _build_user_response(result.user)
        
        return AuthResponse(
            user=user_response,
            tokens=TokenResponse(
                access_token=result.tokens.access_token,
                refresh_token=result.tokens.refresh_token,
                token_type=result.tokens.token_type,
                expires_in=result.tokens.expires_in,
            ),
            is_new_user=result.is_new_user,
        )
        
    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except OAuthProviderNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )


@router.get("/google/callback")
async def google_oauth_callback_redirect(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token for CSRF validation"),
    redirect_uri: Optional[str] = Query(None, description="Frontend redirect URI"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Handle Google OAuth callback via GET redirect.
    
    This endpoint handles the browser redirect from Google.
    It authenticates the user and redirects to the frontend with tokens.
    
    For SPAs, consider using the POST endpoint instead.
    """
    try:
        result = await auth_service.authenticate_oauth(
            provider_name="google",
            code=code,
        )
        
        # Redirect to frontend with tokens
        # In production, use a more secure method (e.g., one-time code)
        frontend_url = redirect_uri or "http://localhost:3000/auth/callback"
        redirect_url = (
            f"{frontend_url}"
            f"?access_token={result.tokens.access_token}"
            f"&refresh_token={result.tokens.refresh_token}"
            f"&is_new_user={str(result.is_new_user).lower()}"
        )
        
        return RedirectResponse(url=redirect_url)
        
    except (OAuthError, OAuthProviderNotConfiguredError) as e:
        # Redirect to frontend with error
        frontend_url = redirect_uri or "http://localhost:3000/auth/callback"
        return RedirectResponse(url=f"{frontend_url}?error={str(e)}")


# ────────────────────────────────
# Token Management
# ────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.
    
    Returns a new token pair. The old refresh token remains valid
    until it expires or is explicitly revoked.
    """
    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )
        
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please login again.",
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    request: LogoutRequest = None,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout current user.
    
    Clears authentication cookies and optionally invalidates tokens.
    """
    # Logout (invalidate tokens if implemented)
    await auth_service.logout(
        user_id=current_user.id,
        token=request.refresh_token if request else None,
    )
    
    # Clear cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/auth")
    
    return LogoutResponse(message="Successfully logged out")


# ────────────────────────────────
# User Profile
# ────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user's profile.
    
    Returns the full user profile including subscription and stats.
    """
    return _build_user_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Update current user's profile.
    
    Allows updating name, avatar, and preferences.
    """
    user_service = UserService(user_repo)
    updated_user = await user_service.update_profile(current_user.id, update)
    
    return _build_user_response(updated_user)


# ────────────────────────────────
# Helper Functions
# ────────────────────────────────

def _build_user_response(user: User) -> UserResponse:
    """Build UserResponse from User model."""
    from app.users.schemas import (
        UserAuthSchema,
        UserSubscriptionSchema,
        UserStatsSchema,
        UserPreferencesSchema,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        auth=UserAuthSchema(
            provider=user.auth.provider if user.auth else None,
            email_verified=user.auth.email_verified if user.auth else False,
        ),
        subscription=UserSubscriptionSchema(
            tier=user.subscription.tier,
            credits=user.subscription.credits,
            credits_reset_at=user.subscription.credits_reset_at,
        ),
        stats=UserStatsSchema(
            books_uploaded=user.stats.books_uploaded,
            total_chats=user.stats.total_chats,
            characters_created=user.stats.characters_created,
            stories_created=user.stats.stories_created,
        ),
        preferences=UserPreferencesSchema(
            theme=user.preferences.theme,
            notifications_enabled=user.preferences.notifications_enabled,
            email_notifications=user.preferences.email_notifications,
            default_chat_mode=user.preferences.default_chat_mode,
            language=user.preferences.language,
        ),
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )

