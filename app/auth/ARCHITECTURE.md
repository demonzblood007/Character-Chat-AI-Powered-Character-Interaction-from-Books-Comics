# Authentication System Architecture

## High-Level Design (HLD)

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Frontend)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  Auth Router    │  │  Protected      │  │  Public                     │  │
│  │  /auth/*        │  │  Routes         │  │  Routes                     │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────────────────┘  │
│           │                    │                                             │
│           ▼                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Authentication Middleware                         │    │
│  │                    (JWT Validation + User Context)                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                    │
│  │ AuthService   │  │ TokenService  │  │ UserService   │                    │
│  │               │  │               │  │               │                    │
│  │ - login()     │  │ - create()    │  │ - create()    │                    │
│  │ - logout()    │  │ - verify()    │  │ - get()       │                    │
│  │ - refresh()   │  │ - refresh()   │  │ - update()    │                    │
│  └───────┬───────┘  └───────────────┘  └───────┬───────┘                    │
│          │                                      │                            │
│          ▼                                      ▼                            │
│  ┌───────────────┐                    ┌───────────────┐                     │
│  │ OAuth         │                    │ User          │                     │
│  │ Providers     │                    │ Repository    │                     │
│  │               │                    │               │                     │
│  │ - Google      │                    │ - MongoDB     │                     │
│  │ - (Future)    │                    │               │                     │
│  └───────────────┘                    └───────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                    │
│  │   MongoDB     │  │    Redis      │  │   (Future)    │                    │
│  │   - users     │  │   - sessions  │  │   - cache     │                    │
│  │   - tokens    │  │   - blacklist │  │               │                    │
│  └───────────────┘  └───────────────┘  └───────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌──────┐     ┌──────────┐     ┌────────┐     ┌──────────┐     ┌─────────┐
│Client│     │API Server│     │Google  │     │Token Svc │     │User Repo│
└──┬───┘     └────┬─────┘     └───┬────┘     └────┬─────┘     └────┬────┘
   │              │               │               │                │
   │ 1. GET /auth/google/url     │               │                │
   │─────────────>│               │               │                │
   │              │               │               │                │
   │ 2. Return OAuth URL         │               │                │
   │<─────────────│               │               │                │
   │              │               │               │                │
   │ 3. Redirect to Google       │               │                │
   │─────────────────────────────>│               │                │
   │              │               │               │                │
   │ 4. User authenticates       │               │                │
   │<─────────────────────────────│               │                │
   │              │               │               │                │
   │ 5. POST /auth/google/callback (code)        │                │
   │─────────────>│               │               │                │
   │              │               │               │                │
   │              │ 6. Exchange code for tokens  │                │
   │              │──────────────>│               │                │
   │              │               │               │                │
   │              │ 7. Return access_token       │                │
   │              │<──────────────│               │                │
   │              │               │               │                │
   │              │ 8. Get user info             │                │
   │              │──────────────>│               │                │
   │              │               │               │                │
   │              │ 9. Return user profile       │                │
   │              │<──────────────│               │                │
   │              │               │               │                │
   │              │ 10. Find/Create user         │                │
   │              │───────────────────────────────────────────────>│
   │              │               │               │                │
   │              │ 11. Return user              │                │
   │              │<───────────────────────────────────────────────│
   │              │               │               │                │
   │              │ 12. Generate JWT tokens      │                │
   │              │──────────────────────────────>│                │
   │              │               │               │                │
   │              │ 13. Return access + refresh  │                │
   │              │<──────────────────────────────│                │
   │              │               │               │                │
   │ 14. Return tokens + user    │               │                │
   │<─────────────│               │               │                │
   │              │               │               │                │
```

## Low-Level Design (LLD)

### SOLID Principles Application

#### S - Single Responsibility Principle
Each class has ONE reason to change:

| Class | Responsibility |
|-------|---------------|
| `GoogleOAuthProvider` | Handle Google OAuth flow only |
| `TokenService` | JWT creation and validation only |
| `UserRepository` | Database operations for users only |
| `UserService` | Business logic for users only |
| `AuthService` | Orchestrate authentication flow only |

#### O - Open/Closed Principle
Open for extension, closed for modification:

```python
# Abstract base - closed for modification
class OAuthProvider(ABC):
    @abstractmethod
    async def get_authorization_url(self) -> str: ...
    
    @abstractmethod
    async def get_user_info(self, code: str) -> OAuthUserInfo: ...

# Extensions - open for new providers
class GoogleOAuthProvider(OAuthProvider): ...
class GitHubOAuthProvider(OAuthProvider): ...  # Future
class AppleOAuthProvider(OAuthProvider): ...   # Future
```

#### L - Liskov Substitution Principle
Any provider can be substituted without breaking the system:

```python
def get_provider(provider_name: str) -> OAuthProvider:
    providers = {
        "google": GoogleOAuthProvider(),
        "github": GitHubOAuthProvider(),  # Works the same
    }
    return providers[provider_name]
```

#### I - Interface Segregation Principle
Small, focused interfaces:

```python
class IUserReader(Protocol):
    async def get_by_id(self, id: str) -> Optional[User]: ...
    async def get_by_email(self, email: str) -> Optional[User]: ...

class IUserWriter(Protocol):
    async def create(self, user: UserCreate) -> User: ...
    async def update(self, id: str, data: UserUpdate) -> User: ...

class IUserRepository(IUserReader, IUserWriter, Protocol):
    """Full repository combines reader and writer"""
    pass
```

#### D - Dependency Inversion Principle
High-level modules depend on abstractions:

```python
class AuthService:
    def __init__(
        self,
        user_repository: IUserRepository,      # Abstraction
        token_service: ITokenService,          # Abstraction
        oauth_provider: OAuthProvider,         # Abstraction
    ):
        self._users = user_repository
        self._tokens = token_service
        self._oauth = oauth_provider
```

### Class Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              <<interface>>                                   │
│                              OAuthProvider                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ + get_authorization_url(state: str) -> str                                  │
│ + exchange_code(code: str) -> OAuthTokens                                   │
│ + get_user_info(access_token: str) -> OAuthUserInfo                         │
│ + get_provider_name() -> str                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      △
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
        ┌───────────┴───────────┐         ┌────────────┴────────────┐
        │  GoogleOAuthProvider  │         │  (Future Providers)     │
        ├───────────────────────┤         └─────────────────────────┘
        │ - client_id: str      │
        │ - client_secret: str  │
        │ - redirect_uri: str   │
        └───────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                   User                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ + id: ObjectId                                                              │
│ + email: str                                                                │
│ + name: str                                                                 │
│ + avatar_url: Optional[str]                                                 │
│ + auth_provider: AuthProvider                                               │
│ + auth_provider_id: str                                                     │
│ + subscription: SubscriptionTier                                            │
│ + credits: int                                                              │
│ + books_uploaded: int                                                       │
│ + total_chats: int                                                          │
│ + created_at: datetime                                                      │
│ + updated_at: datetime                                                      │
│ + last_login_at: datetime                                                   │
│ + is_active: bool                                                           │
│ + is_verified: bool                                                         │
│ + preferences: UserPreferences                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              TokenService                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ - secret_key: str                                                           │
│ - algorithm: str                                                            │
│ - access_token_expire: int                                                  │
│ - refresh_token_expire: int                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ + create_access_token(user_id: str, data: dict) -> str                      │
│ + create_refresh_token(user_id: str) -> str                                 │
│ + verify_token(token: str) -> TokenPayload                                  │
│ + create_token_pair(user_id: str) -> TokenPair                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              AuthService                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ - user_repository: IUserRepository                                          │
│ - token_service: TokenService                                               │
│ - oauth_providers: Dict[str, OAuthProvider]                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ + get_oauth_url(provider: str, state: str) -> str                           │
│ + authenticate_oauth(provider: str, code: str) -> AuthResult                │
│ + refresh_tokens(refresh_token: str) -> TokenPair                           │
│ + logout(user_id: str, token: str) -> bool                                  │
│ + get_current_user(token: str) -> User                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema

```javascript
// users collection
{
  "_id": ObjectId,
  "email": "user@example.com",           // unique, indexed
  "name": "John Doe",
  "avatar_url": "https://...",
  
  // Authentication
  "auth": {
    "provider": "google",                 // enum: google, github, email
    "provider_id": "google-user-id-123",  // indexed
    "email_verified": true
  },
  
  // Subscription & Credits
  "subscription": {
    "tier": "free",                       // enum: free, pro, premium
    "credits": 100,
    "credits_reset_at": ISODate,
    "started_at": ISODate,
    "expires_at": ISODate
  },
  
  // Usage Stats
  "stats": {
    "books_uploaded": 0,
    "total_chats": 0,
    "characters_created": 0
  },
  
  // User Preferences
  "preferences": {
    "theme": "dark",
    "notifications_enabled": true,
    "default_chat_mode": "casual"
  },
  
  // Status
  "is_active": true,
  "is_verified": true,
  
  // Timestamps
  "created_at": ISODate,
  "updated_at": ISODate,
  "last_login_at": ISODate
}

// Indexes
db.users.createIndex({ "email": 1 }, { unique: true })
db.users.createIndex({ "auth.provider": 1, "auth.provider_id": 1 }, { unique: true })
db.users.createIndex({ "created_at": -1 })
```

### API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/auth/google/url` | Get Google OAuth URL | No |
| POST | `/auth/google/callback` | Exchange code for tokens | No |
| POST | `/auth/refresh` | Refresh access token | Refresh Token |
| POST | `/auth/logout` | Logout user | Access Token |
| GET | `/auth/me` | Get current user | Access Token |
| PATCH | `/auth/me` | Update current user | Access Token |

### Security Considerations

1. **JWT Tokens**: Short-lived access tokens (15 min), long-lived refresh tokens (7 days)
2. **Token Storage**: Refresh tokens stored in httpOnly cookies
3. **CSRF Protection**: State parameter in OAuth flow
4. **Rate Limiting**: Limit auth endpoints to prevent abuse
5. **Token Blacklist**: Redis-based blacklist for logged-out tokens

