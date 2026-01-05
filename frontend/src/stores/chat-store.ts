/**
 * Production-Grade Chat State Management
 * Features:
 * - Complete session isolation per character
 * - Persistent chat history with localStorage
 * - Real-time streaming support
 * - Memory management and cleanup
 * - Production-ready error handling
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { ChatMessage, Character, api } from "@/lib/api";

interface ChatSession {
  characterId: string;
  characterName: string;
  sessionId: string;
  messages: ChatMessage[];
  lastActivity: string;
  memoriesUsed: number;
  tokensUsed: number;
  isNewSession: boolean;
}

interface ChatState {
  // Current active chat
  currentCharacter: Character | null;
  currentSession: ChatSession | null;

  // All sessions (persisted)
  sessions: Record<string, ChatSession>;

  // UI state
  isTyping: boolean;
  streamingContent: string;
  statusMessage: string;
  error: string | null;

  // Actions
  setCharacter: (character: Character) => void;
  sendMessage: (message: string) => Promise<void>;
  clearCurrentChat: () => void;
  loadCharacterSession: (characterId: string) => void;

  // Utilities
  getCharacterMessages: (characterId: string) => ChatMessage[];
  getRecentChats: () => ChatSession[];
  getSessionStats: (characterId: string) => { memories: number; tokens: number; messages: number };

  // Error handling
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      currentCharacter: null,
      currentSession: null,
      sessions: {},
      isTyping: false,
      streamingContent: "",
      statusMessage: "",
      error: null,

      setCharacter: (character) => {
        const { loadCharacterSession } = get();
        set({ currentCharacter: character, error: null });
        loadCharacterSession(character.name);
      },

      loadCharacterSession: (characterId) => {
        const { sessions } = get();
        const existingSession = sessions[characterId];

        if (existingSession) {
          // Load existing session
          set({ currentSession: existingSession });
        } else {
          // Create new session
          const newSession: ChatSession = {
            characterId,
            characterName: characterId,
            sessionId: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            messages: [],
            lastActivity: new Date().toISOString(),
            memoriesUsed: 0,
            tokensUsed: 0,
            isNewSession: true,
          };

          set((state) => ({
            sessions: { ...state.sessions, [characterId]: newSession },
            currentSession: newSession,
          }));
        }
      },

      sendMessage: async (message) => {
        const { currentSession, currentCharacter } = get();
        if (!currentSession || !currentCharacter) {
          throw new Error("No active chat session");
        }

        set({ isTyping: true, streamingContent: "", statusMessage: "", error: null });

        try {
          // Add user message immediately
          const userMessage: ChatMessage = {
            content: message,
            role: "user",
            timestamp: new Date().toISOString(),
            character_name: currentCharacter.name,
          };

          // Update current session with user message
          const updatedSession = {
            ...currentSession,
            messages: [...currentSession.messages, userMessage],
            lastActivity: new Date().toISOString(),
          };

        // Force re-render by triggering state update
        set((state) => ({
          sessions: { ...state.sessions, [currentSession.characterId]: updatedSession },
          currentSession: updatedSession,
        }));

          // Send to API and get streaming response
          const cleanup = api.streamChat(
            {
              character_name: currentCharacter.name,
              message,
              session_id: currentSession.sessionId,
            },
            (chunk) => {
              set((state) => ({
                streamingContent: state.streamingContent + chunk
              }));
            },
            (status) => {
              set({ statusMessage: status });
            },
            (done) => {
          // Add the complete assistant message
          const { streamingContent } = get();
              const assistantMessage: ChatMessage = {
                content: streamingContent,
                role: "assistant",
                timestamp: new Date().toISOString(),
                character_name: currentCharacter.name,
              };

              // Update session with assistant message and API response data
              const finalSession = {
                ...updatedSession,
                sessionId: done.session_id || currentSession.sessionId,
                messages: [...updatedSession.messages, assistantMessage],
                lastActivity: new Date().toISOString(),
                memoriesUsed: done.memories_used || currentSession.memoriesUsed,
                tokensUsed: done.tokens_used || currentSession.tokensUsed,
                isNewSession: false,
              };

              set((state) => ({
                sessions: { ...state.sessions, [currentSession.characterId]: finalSession },
                currentSession: finalSession,
                isTyping: false,
                streamingContent: "",
                statusMessage: "",
              }));
            },
            (error) => {
              console.error("Chat streaming error:", error);
              set({
                isTyping: false,
                streamingContent: "",
                statusMessage: "",
                error: "Failed to get response. Please try again."
              });
            }
          );

          // Note: cleanup function available for stream abortion if needed

        } catch (error) {
          console.error("Failed to send message:", error);
          set({
            isTyping: false,
            streamingContent: "",
            statusMessage: "",
            error: error instanceof Error ? error.message : "Failed to send message"
          });
          throw error;
        }
      },

      clearCurrentChat: () => {
        const { currentSession } = get();
        if (!currentSession) return;

        // Clear messages but keep session structure
        const clearedSession = {
          ...currentSession,
          messages: [],
          lastActivity: new Date().toISOString(),
          memoriesUsed: 0,
          tokensUsed: 0,
          isNewSession: true,
        };

        set((state) => ({
          sessions: { ...state.sessions, [currentSession.characterId]: clearedSession },
          currentSession: clearedSession,
          error: null,
        }));
      },

      getCharacterMessages: (characterId) => {
        const { sessions } = get();
        return sessions[characterId]?.messages || [];
      },

      getRecentChats: () => {
        const { sessions } = get();
        console.log("📋 Chat store sessions:", Object.keys(sessions));
        const recentChats = Object.values(sessions)
          .filter(session => session.messages.length > 0)
          .sort((a, b) => new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime())
          .slice(0, 10); // Return top 10 recent chats
        console.log("📋 Recent chats:", recentChats.length);
        return recentChats;
      },

      getSessionStats: (characterId) => {
        const { sessions } = get();
        const session = sessions[characterId];
        return {
          memories: session?.memoriesUsed || 0,
          tokens: session?.tokensUsed || 0,
          messages: session?.messages.length || 0,
        };
      },

      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: "chat-store",
      partialize: (state) => ({
        sessions: state.sessions,
      }),
    }
  )
);

