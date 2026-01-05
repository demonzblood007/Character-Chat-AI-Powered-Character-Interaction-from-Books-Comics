"""
JWT Token Service
=================

Handles JWT token creation and validation.

Single Responsibility: Only deals with JWT operations.
"""

import jwt
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

from ..config import JWTConfig
from ..exceptions import TokenExpiredError, InvalidTokenError


class TokenType(str, Enum):
    """Types of JWT tokens."""
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class TokenPayload:
    """
    Decoded JWT token payload.
    """
    user_id: str
    token_type: TokenType
    exp: datetime
    iat: datetime
    jti: Optional[str] = None  # JWT ID for blacklisting
    
    # Additional claims
    email: Optional[str] = None
    name: Optional[str] = None


@dataclass
class TokenPair:
    """
    Access and refresh token pair.
    """
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 0  # Seconds until access token expires


class TokenService:
    """
    JWT token service.
    
    Handles:
    - Creating access and refresh tokens
    - Validating tokens
    - Extracting payloads
    """
    
    def __init__(self, config: JWTConfig):
        """
        Initialize token service.
        
        Args:
            config: JWT configuration
        """
        self._config = config
    
    def create_access_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an access token.
        
        Args:
            user_id: User's ID
            additional_claims: Extra data to include in token
            
        Returns:
            Encoded JWT access token
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self._config.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "type": TokenType.ACCESS.value,
            "iat": now,
            "exp": expires,
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self._config.secret_key, algorithm=self._config.algorithm)
    
    def create_refresh_token(self, user_id: str, jti: Optional[str] = None) -> str:
        """
        Create a refresh token.
        
        Args:
            user_id: User's ID
            jti: Optional JWT ID for tracking/blacklisting
            
        Returns:
            Encoded JWT refresh token
        """
        import uuid
        
        now = datetime.utcnow()
        expires = now + timedelta(days=self._config.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "type": TokenType.REFRESH.value,
            "iat": now,
            "exp": expires,
            "jti": jti or str(uuid.uuid4()),
        }
        
        return jwt.encode(payload, self._config.secret_key, algorithm=self._config.algorithm)
    
    def create_token_pair(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> TokenPair:
        """
        Create both access and refresh tokens.
        
        Args:
            user_id: User's ID
            additional_claims: Extra data for access token
            
        Returns:
            Token pair with access and refresh tokens
        """
        access_token = self.create_access_token(user_id, additional_claims)
        refresh_token = self.create_refresh_token(user_id)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=self._config.access_token_expire_minutes * 60,
        )
    
    def verify_token(self, token: str, expected_type: Optional[TokenType] = None) -> TokenPayload:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            expected_type: Optional expected token type (access/refresh)
            
        Returns:
            Decoded token payload
            
        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self._config.secret_key,
                algorithms=[self._config.algorithm]
            )
            
            # Check token type if specified
            token_type = TokenType(payload.get("type", "access"))
            if expected_type and token_type != expected_type:
                raise InvalidTokenError(f"Expected {expected_type.value} token, got {token_type.value}")
            
            return TokenPayload(
                user_id=payload["sub"],
                token_type=token_type,
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                jti=payload.get("jti"),
                email=payload.get("email"),
                name=payload.get("name"),
            )
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
    
    def verify_access_token(self, token: str) -> TokenPayload:
        """
        Verify an access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Decoded token payload
        """
        return self.verify_token(token, TokenType.ACCESS)
    
    def verify_refresh_token(self, token: str) -> TokenPayload:
        """
        Verify a refresh token.
        
        Args:
            token: JWT refresh token
            
        Returns:
            Decoded token payload
        """
        return self.verify_token(token, TokenType.REFRESH)
    
    def decode_token_unsafe(self, token: str) -> dict:
        """
        Decode token without verification.
        
        Useful for debugging or getting claims from expired tokens.
        DO NOT use for authentication decisions.
        
        Args:
            token: JWT token
            
        Returns:
            Decoded payload dict
        """
        return jwt.decode(token, options={"verify_signature": False})

