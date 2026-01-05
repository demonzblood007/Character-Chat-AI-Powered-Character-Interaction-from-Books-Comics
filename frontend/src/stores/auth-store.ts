/**
 * Authentication State Store
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/lib/api";
import { auth } from "@/lib/auth";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,

      setUser: (user) => {
        set({ user, isAuthenticated: !!user });
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      login: async () => {
        set({ isLoading: true });
        try {
          console.log("🚀 Starting Google OAuth flow...");
          await auth.startGoogleAuth();
          // Note: This line won't execute because startGoogleAuth() redirects
          console.log("✅ Redirecting to Google...");
        } catch (error) {
          console.error("❌ Login failed:", error);
          set({ isLoading: false });

          // Show user-friendly error message
          const errorMessage = error instanceof Error ? error.message : "Failed to start authentication";
          alert(`Authentication Error: ${errorMessage}\n\nPlease make sure the backend server is running on port 8000.`);

          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await auth.logout();
          set({ user: null, isAuthenticated: false });
        } finally {
          set({ isLoading: false });
        }
      },

      checkAuth: async () => {
        set({ isLoading: true });
        console.log("🔍 Checking authentication...");

        // Check token availability
        const token = localStorage.getItem("access_token");
        console.log("🔑 Token in localStorage:", token ? "present" : "missing");

        try {
          const user = await auth.getCurrentUser();
          console.log("✅ User authenticated:", user);
          set({
            user,
            isAuthenticated: !!user,
            isLoading: false
          });
        } catch (error) {
          console.log("❌ Authentication check failed:", error);
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false
          });
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ 
        user: state.user,
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);

