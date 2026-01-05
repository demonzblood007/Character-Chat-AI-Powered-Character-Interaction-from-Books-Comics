# Frontend-Backend Integration QA Report

## Files Inspected
- `character-chat/package.json` - Stack identification
- `character-chat/src/lib/api.ts` - API client and endpoint definitions
- `character-chat/src/lib/auth.ts` - Authentication logic
- `character-chat/src/app/(auth)/login/page.tsx` - Login UI
- `character-chat/src/app/(auth)/callback/page.tsx` - OAuth callback handler
- `character-chat/src/app/(main)/chat/[character]/page.tsx` - Chat UI
- `character-chat/src/stores/auth-store.ts` - Auth state management
- `character-chat/src/stores/chat-store.ts` - Chat state management

---

## 1. Frontend Stack + Run Instructions

**Framework**: Next.js 16.1.1 (App Router)
**React Version**: 19.2.3
**Build Tool**: Next.js built-in (no Vite/CRA)

**Install & Run Commands**:
```bash
cd character-chat
npm install
npm run dev
```

**Default Port**: `3000` (Next.js default)
**Access URL**: `http://localhost:3000`

---

## 2. Backend Base URL Configuration

**Configuration Location**: `character-chat/src/lib/api.ts:6`

**Environment Variable**:
- `NEXT_PUBLIC_API_URL` (optional)
- **Default**: `http://localhost:8000`

**Example `.env.local`**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Status**: ✅ Frontend correctly defaults to `http://localhost:8000`

---

## 3. Auth Wiring (Google OAuth)

### Login Flow

**Login Button Location**: `character-chat/src/app/(auth)/login/page.tsx:124`
- Button calls `useAuthStore().login()`

**Auth Initiation**: `character-chat/src/lib/auth.ts:79-91`
- Calls `GET /auth/google/url`
- Stores `state` in `sessionStorage` (key: `"oauth_state"`)
- Redirects browser to `authorization_url` from backend

### Token Storage

**Storage Method**: `localStorage` (not cookies)
- `access_token` → `localStorage.getItem("access_token")`
- `refresh_token` → `localStorage.getItem("refresh_token")`
- `token_expiry` → `localStorage.getItem("token_expiry")` (calculated expiry timestamp)

**Location**: `character-chat/src/lib/auth.ts:14-43`

### Callback Handler

**Route**: `/callback` (Next.js page: `character-chat/src/app/(auth)/callback/page.tsx`)

**Expected Query Parameters**:
- `code` (string) - OAuth authorization code from Google
- `state` (string) - OAuth state parameter (validated against sessionStorage)

**Callback Flow**:
1. Frontend receives: `http://localhost:3000/callback?code=XXX&state=YYY`
2. Validates `state` against `sessionStorage.getItem("oauth_state")`
3. Calls `POST /auth/google/callback` with `{ code, state }`
4. Backend returns `{ user, tokens }`
5. Stores tokens in `localStorage`
6. Redirects to `/dashboard`

**Location**: `character-chat/src/app/(auth)/callback/page.tsx:18-46` and `character-chat/src/lib/auth.ts:95-108`

### Redirect Flow Summary

```
Frontend /login 
  → Backend GET /auth/google/url 
  → Google OAuth 
  → Backend POST /auth/google/callback 
  → Frontend /callback?code=XXX&state=YYY 
  → Frontend /dashboard
```

**Expected Callback URL Format**: 
- Host: `http://localhost:3000` (or configured frontend URL)
- Route: `/callback`
- Parameters: `code` (OAuth code), `state` (OAuth state)

**Status**: ✅ OAuth flow is properly wired

---

## 4. v2 Chat Wiring

### ⚠️ CRITICAL FINDING: v2 Endpoints NOT Implemented

**Current Implementation**:
- Uses `/chat/stream` (v1 endpoint)
- Uses `/chat` (v1 endpoint, non-streaming fallback)
- Uses `/chat/history` (v1 endpoint)

**Missing v2 Endpoints**:
- ❌ `/v2/chat` - Not implemented
- ❌ `/v2/chat/stream` - Not implemented (using `/chat/stream` instead)
- ❌ `/v2/chat/summary` - Not implemented
- ❌ `/v2/chat/metrics` - Not implemented
- ❌ `/v2/chat/memories` - Not implemented

**Current Chat Implementation**:

**Location**: `character-chat/src/lib/api.ts:230-307`

**Streaming Method**: Uses `fetch` with `ReadableStream` (NOT EventSource)
- ✅ Correct for POST requests with body
- ⚠️ Note: Code has unused `EventSource` reference (lines 240-243, never actually used)

**Request Shape**: 
```typescript
{
  character_name: string;
  message: string;
}
```
**Location**: `character-chat/src/lib/api.ts:68-71`

**Response Format** (streaming):
- Expects Server-Sent Events format: `data: {...}\n`
- Parses JSON: `{ type: "chunk" | "status" | "done", content?: string, message?: string }`
- **Location**: `character-chat/src/lib/api.ts:279-293`

**Missing Response Fields**:
- ❌ No `session_id` handling
- ❌ No `memories_used` field
- ❌ Response shape doesn't match v2 schema expectations

**Status**: ❌ **BREAKING POINT** - Frontend uses v1 endpoints, backend expects v2

---

## 5. CORS / Cookies / Headers

### Authentication Method

**Method**: Bearer Token (JWT) in Authorization header
- ✅ NOT using cookies
- ✅ NOT using `credentials: 'include'`

**Implementation**: `character-chat/src/lib/api.ts:81-85`
```typescript
Authorization: `Bearer ${localStorage.getItem("access_token")}`
```

### Headers

**Standard Headers**:
- `Content-Type: application/json` (for JSON requests)
- `Authorization: Bearer <token>` (when authenticated)

**Custom Headers**: None
- ❌ No `X-User-ID` header
- ✅ Uses JWT from Authorization header (v2 compatible)

**CORS Requirements**:
- Frontend expects backend to allow requests from `http://localhost:3000`
- No `credentials: 'include'` used, so simple CORS should work

**Status**: ✅ Token-based auth is properly implemented (no legacy headers)

---

## 6. Smoke Test Plan (5 minutes)

### Prerequisites
1. Backend running on `http://localhost:8000`
2. Frontend running on `http://localhost:3000`
3. Backend has Google OAuth configured

### Test Steps

1. **Start Services**
   ```bash
   # Terminal 1: Backend
   # (Start your FastAPI backend on port 8000)
   
   # Terminal 2: Frontend
   cd character-chat
   npm run dev
   ```

2. **Test OAuth Login**
   - Navigate to `http://localhost:3000/login`
   - Click "Continue with Google"
   - Complete Google OAuth flow
   - ✅ Verify redirect to `/callback` with `code` and `state` params
   - ✅ Verify redirect to `/dashboard` after successful auth
   - ✅ Verify tokens stored in `localStorage` (DevTools → Application → Local Storage)

3. **Test Chat (v1 endpoints - will fail if backend only has v2)**
   - Navigate to `/chat/[character-name]` (e.g., `/chat/TestCharacter`)
   - Send a message: "Hello"
   - ⚠️ **Expected Failure**: Frontend calls `/chat/stream` but backend may only have `/v2/chat/stream`
   - Check browser console for errors
   - Check Network tab for failed requests

4. **Verify Token Usage**
   - Open DevTools → Network tab
   - Filter by "chat"
   - ✅ Verify `Authorization: Bearer <token>` header present
   - ✅ Verify request to `/chat/stream` (or check if 404/500 if v2 only)

5. **Check Memory Endpoints** (if backend has v2)
   - ❌ Frontend has no UI/code for `/v2/chat/summary`, `/v2/chat/metrics`, `/v2/chat/memories`
   - These endpoints are not callable from the frontend

**Expected Result**: 
- ✅ OAuth flow should work
- ❌ Chat will fail if backend only exposes v2 endpoints
- ❌ Memory endpoints not accessible from UI

---

## 7. If Broken: First Failure Point + Likely Fix

### Primary Breaking Point

**Failing Request**: `POST /chat/stream`

**Expected Error**:
- **Status Code**: `404 Not Found` (if backend only has `/v2/chat/stream`)
- **OR**: `500 Internal Server Error` (if endpoint exists but schema mismatch)
- **Error Body**: `{"detail": "Not Found"}` or backend error message

**Root Cause**: 
- Frontend uses v1 endpoints (`/chat/stream`)
- Backend exposes v2 endpoints (`/v2/chat/stream`)
- **Endpoint mismatch**

**Simplest Fix**:
Update API client to use v2 endpoints:

**File**: `character-chat/src/lib/api.ts`

1. Change line 238:
   ```typescript
   const url = `${this.baseUrl}/v2/chat/stream`;  // Changed from /chat/stream
   ```

2. Change line 223:
   ```typescript
   return this.request("/v2/chat", {  // Changed from /chat
   ```

3. Update response parsing to handle v2 schema (if different):
   - Add `session_id` handling
   - Add `memories_used` field handling
   - Verify response shape matches backend v2 schema

**Additional Required Changes** (if v2 schema differs):
- Update `ChatRequest` interface to include `session_id?` (if needed)
- Update response parsing in `streamChat` to handle v2 response format
- Add API methods for `/v2/chat/summary`, `/v2/chat/metrics`, `/v2/chat/memories` if UI needs them

### Secondary Issues

**Missing Memory Endpoints**:
- Frontend has no implementation for `/v2/chat/summary`, `/v2/chat/metrics`, `/v2/chat/memories`
- **Fix**: Implement API client methods and UI components if required

**OAuth Callback URL**:
- Backend must redirect to `http://localhost:3000/callback?code=XXX&state=YYY`
- **Fix**: Ensure backend `GOOGLE_REDIRECT_URI` or callback configuration matches frontend URL

**CORS**:
- If CORS errors occur, backend must allow `http://localhost:3000`
- **Fix**: Update FastAPI CORS middleware to include frontend origin

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Stack Identification | ✅ | Next.js 16.1.1, runs on port 3000 |
| API URL Configuration | ✅ | Uses NEXT_PUBLIC_API_URL, defaults to localhost:8000 |
| OAuth Flow | ✅ | Properly wired, uses localStorage for tokens |
| v2 Chat Endpoints | ❌ | **Using v1 endpoints, backend expects v2** |
| Streaming Implementation | ✅ | Uses fetch streaming (correct for POST) |
| Memory Endpoints | ❌ | Not implemented in frontend |
| Auth Headers | ✅ | Bearer tokens, no legacy headers |

**Critical Action Required**: Update chat endpoints from `/chat/*` to `/v2/chat/*` in `character-chat/src/lib/api.ts`

