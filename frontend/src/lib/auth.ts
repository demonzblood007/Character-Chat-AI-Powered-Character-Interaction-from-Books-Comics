/**
 * Authentication Utilities
 * Handles token management and auth state
 */

import { api, AuthTokens, User } from "./api";

const TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const TOKEN_EXPIRY_KEY = "token_expiry";

export const auth = {
  // Get stored tokens
  getAccessToken(): string | null {
    if (typeof window === "undefined") return null;

    // Try multiple storage locations for compatibility
    const token = localStorage.getItem(TOKEN_KEY) ||
                  localStorage.getItem("access_token") ||
                  sessionStorage.getItem("access_token");

    console.log("🔑 Auth utility - token sources:", {
      TOKEN_KEY: !!localStorage.getItem(TOKEN_KEY),
      access_token: !!localStorage.getItem("access_token"),
      sessionStorage: !!sessionStorage.getItem("access_token"),
      final: token ? "present" : "missing"
    });

    return token;
  },

  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  // Store tokens
  setTokens(tokens: AuthTokens): void {
    if (typeof window === "undefined") return;
    
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    
    // Calculate and store expiry time
    const expiryTime = Date.now() + tokens.expires_in * 1000;
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
  },

  // Clear tokens
  clearTokens(): void {
    if (typeof window === "undefined") return;
    
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
  },

  // Check if token is expired
  isTokenExpired(): boolean {
    if (typeof window === "undefined") return true;
    
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
    if (!expiry) return true;
    
    // Add 60 second buffer
    return Date.now() >= parseInt(expiry, 10) - 60000;
  },

  // Check if user is authenticated
  isAuthenticated(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;
    return !this.isTokenExpired();
  },

  // Refresh the access token
  async refreshAccessToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const tokens = await api.refreshToken(refreshToken);
      this.setTokens(tokens);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  },

  // Start Google OAuth flow
  async startGoogleAuth(): Promise<void> {
    try {
      const { authorization_url, state } = await api.getGoogleAuthUrl();
      
      // Store state for verification
      sessionStorage.setItem("oauth_state", state);
      
      // Redirect to Google
      window.location.href = authorization_url;
    } catch (error) {
      console.error("Failed to start Google auth:", error);
      throw error;
    }
  },

  // Handle Google OAuth callback
  async handleCallback(code: string, state: string): Promise<User> {
    // Verify state
    const storedState = sessionStorage.getItem("oauth_state");
    if (state !== storedState) {
      throw new Error("Invalid OAuth state");
    }
    
    sessionStorage.removeItem("oauth_state");
    
    const { user, tokens } = await api.googleCallback(code, state);
    this.setTokens(tokens);
    
    return user;
  },

  // Logout
  async logout(): Promise<void> {
    try {
      await api.logout();
    } catch {
      // Ignore logout errors
    } finally {
      this.clearTokens();
    }
  },

  // Get current user with auto-refresh
  async getCurrentUser(): Promise<User | null> {
    if (!this.isAuthenticated()) {
      // Try to refresh token
      const refreshed = await this.refreshAccessToken();
      if (!refreshed) return null;
    }

    try {
      return await api.getCurrentUser();
    } catch {
      this.clearTokens();
      return null;
    }
  },
};

