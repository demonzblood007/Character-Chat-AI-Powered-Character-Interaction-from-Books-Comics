/**
 * API Client for Character Chat Backend
 * Base URL: http://localhost:8000
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "access_token"; // Ensure consistency

console.log("🌐 API Base URL configured as:", API_BASE_URL);

// For debugging - try to make a direct test call
if (typeof window !== "undefined") {
  console.log("🔍 Testing API connectivity...");
  fetch(`${API_BASE_URL}/health`)
    .then(response => {
      console.log("✅ API connectivity test successful:", response.status);
      return response.text();
    })
    .then(text => console.log("📄 Health response:", text))
    .catch(error => {
      console.error("❌ API connectivity test failed:", error);
      console.error("💡 This suggests the backend is not accessible from the frontend");
    });

  // Test OAuth endpoint specifically
  setTimeout(() => {
    console.log("🔐 Testing OAuth endpoint...");
    fetch(`${API_BASE_URL}/auth/google/url`)
      .then(response => {
        console.log("✅ OAuth endpoint accessible:", response.status);
        return response.json().catch(() => ({}));
      })
      .then(data => console.log("📄 OAuth response:", data))
      .catch(error => {
        console.error("❌ OAuth endpoint test failed:", error);
        console.error("💡 This means the OAuth endpoint is not working");
      });
  }, 2000);
}

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string;
  subscription: {
    tier: "free" | "pro" | "premium";
    credits: number;
  };
  stats: {
    books_uploaded: number;
    total_chats: number;
    characters_created: number;
  };
  preferences: {
    theme: "dark" | "light";
    notifications_enabled: boolean;
  };
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface Character {
  name: string;
  description: string;
  powers: string[];
  story_arcs: string[];
  avatar: string;
  relationships: {
    target: string;
    type: "ally" | "enemy" | "neutral" | "family" | "friend" | "lover";
  }[];
}

export interface BookFile {
  id: string;
  filename: string;
  upload_date: string;
  status: "queued" | "processing" | "extracting_characters" | "extracting_relationships" | "done" | "failed";
  character_count?: number;
  relationship_count?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  character_name?: string;
}

export interface ChatRequest {
  character_name: string;
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  content: string;
  session_id: string;
  memories_used?: number;
  tokens_used?: number;
  is_new_session?: boolean;
}

export interface ChatSummary {
  character_name: string;
  total_messages: number;
  last_activity: string;
  key_topics: string[];
  personality_insights: string[];
}

export interface ChatMetrics {
  total_sessions: number;
  total_messages: number;
  total_tokens: number;
  total_memories: number;
  characters_interacted: number;
}

// API Client Class
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeader(): HeadersInit {
    if (typeof window === "undefined") return {};

    // Try multiple token sources
    const token = localStorage.getItem("access_token") ||
                  localStorage.getItem(TOKEN_KEY) ||
                  sessionStorage.getItem("access_token");

    console.log("🔑 API Client: Token sources checked:", {
      localStorage_access_token: !!localStorage.getItem("access_token"),
      localStorage_TOKEN_KEY: !!localStorage.getItem(TOKEN_KEY),
      sessionStorage: !!sessionStorage.getItem("access_token"),
      final_token: token ? "present" : "missing"
    });

    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...this.getAuthHeader(),
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = "An error occurred";
      let errorDetails = {};

      try {
        const errorResponse = await response.json();
        errorDetails = errorResponse;

        // Extract meaningful error message
        errorMessage = errorResponse.detail ||
                      errorResponse.message ||
                      errorResponse.error ||
                      `HTTP ${response.status}: ${response.statusText}`;

        // If it's still generic, try to stringify the whole response
        if (errorMessage === "An error occurred" && Object.keys(errorResponse).length > 0) {
          errorMessage = JSON.stringify(errorResponse);
        }
      } catch (parseError) {
        // If we can't parse JSON, use status text
        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        console.warn("Failed to parse error response:", parseError);
      }

      console.error("API Error:", {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        errorMessage,
        errorDetails
      });

      throw new ApiError(errorMessage, response.status);
    }

    // Handle empty responses
    const text = await response.text();
    return text ? JSON.parse(text) : ({} as T);
  }

  // Health Check
  async healthCheck(): Promise<{ status: string }> {
    return this.request("/health");
  }

  // Auth Endpoints
  async getGoogleAuthUrl(): Promise<{ authorization_url: string; state: string }> {
    console.log("🔗 Requesting Google auth URL from:", `${this.baseUrl}/auth/google/url`);

    // First check if backend is reachable
    try {
      console.log("🏥 Testing backend health...");
      const healthResponse = await this.healthCheck();
      console.log("✅ Backend health response:", healthResponse);
      console.log("✅ Backend is reachable");
    } catch (healthError) {
      console.error("❌ Backend health check failed:", healthError);
      const errorMessage = healthError instanceof Error ? healthError.message : String(healthError);
      const errorStatus = (healthError as any)?.status;
      console.error("❌ Health check error details:", {
        url: `${this.baseUrl}/health`,
        error: errorMessage,
        status: errorStatus
      });
      throw new Error("Backend server is not running or not responding. Please check that the backend is started on port 8000.");
    }

    try {
      console.log("🔐 Requesting Google auth URL...");
      const result = await this.request<{ authorization_url: string; state: string }>("/auth/google/url");
      console.log("✅ Google auth URL received:", result);
      return result;
    } catch (authError) {
      console.error("❌ Google auth URL request failed:", authError);
      throw new Error("Failed to get Google authentication URL. Please check backend configuration.");
    }
  }

  async googleCallback(code: string, state: string): Promise<AuthResponse> {
    return this.request("/auth/google/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    });
  }

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    return this.request("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async logout(): Promise<void> {
    return this.request("/auth/logout", { method: "POST" });
  }

  async getCurrentUser(): Promise<User> {
    return this.request("/auth/me");
  }

  async updateProfile(data: Partial<User["preferences"]>): Promise<User> {
    return this.request("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  // File Endpoints
  async uploadFile(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<BookFile> {
    const formData = new FormData();
    formData.append("file", file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${this.baseUrl}/upload`);

      const token = localStorage.getItem("access_token");
      if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      }

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = Math.round((event.loaded / event.total) * 100);
          onProgress(progress);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new ApiError("Upload failed", xhr.status));
        }
      };

      xhr.onerror = () => reject(new ApiError("Network error", 0));
      xhr.send(formData);
    });
  }

  async getFiles(): Promise<BookFile[]> {
    return this.request("/files");
  }

  async getFileStatus(fileId: string): Promise<BookFile> {
    return this.request(`/files/${fileId}`);
  }

  // Delete endpoints
  async deleteFile(fileId: string): Promise<{
    ok: boolean;
    deleted_file_id: string;
    deleted_chat_sessions?: number;
    deleted_memories?: number;
    deleted_entities?: number;
    deleted_qdrant_chunks?: number;
    deleted_qdrant_memories?: number;
    character_names?: string[];
  }> {
    return this.request(`/files/${fileId}`, {
      method: "DELETE",
    });
  }

  // Character Endpoints
  async getCharacters(fileId: string): Promise<Character[]> {
    return this.request(`/characters?file_id=${fileId}`);
  }

  async getCharacter(name: string): Promise<Character> {
    return this.request(`/characters/${encodeURIComponent(name)}`);
  }

  async getCharacterRelationships(
    name: string
  ): Promise<Character["relationships"]> {
    return this.request(`/characters/${encodeURIComponent(name)}/relationships`);
  }

  async getCharacterStatus(
    name: string
  ): Promise<{ ready: boolean; status: string }> {
    return this.request(`/characters/${encodeURIComponent(name)}/status`);
  }

  // Chat Endpoints (v2)
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return this.request("/v2/chat", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  // Streaming Chat with SSE (v2)
  streamChat(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
    onStatus?: (status: string) => void,
    onDone?: (done: { session_id?: string; memories_used?: number; tokens_used?: number }) => void,
    onError?: (error: Error) => void
  ): () => void {
    const token = localStorage.getItem("access_token");
    const url = `${this.baseUrl}/v2/chat/stream`;

    // Use fetch with ReadableStream for POST streaming
    const controller = new AbortController();

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Stream request failed");
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No readable stream");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === "status" && onStatus) {
                  onStatus(data.message || data.status);
                } else if (data.type === "chunk") {
                  onChunk(data.content);
                } else if (data.type === "start") {
                  // Stream started
                  if (onStatus) onStatus("Starting conversation...");
                } else if (data.type === "done" && onDone) {
                  onDone({
                    session_id: data.session_id,
                    memories_used: data.memories_used,
                    tokens_used: data.tokens_used,
                  });
                } else if (data.type === "error") {
                  throw new Error(data.message || "Stream error");
                }
              } catch (parseError) {
                console.warn("Failed to parse SSE data:", line, parseError);
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name !== "AbortError" && onError) {
          onError(error);
        }
      });

    // Return abort function
    return () => {
      controller.abort();
    };
  }

  // Memory Endpoints (v2)
  async getChatSummary(characterName: string): Promise<ChatSummary> {
    return this.request(`/v2/chat/summary?character=${encodeURIComponent(characterName)}`);
  }

  async getChatMetrics(): Promise<ChatMetrics> {
    return this.request("/v2/chat/metrics");
  }

  async clearCharacterMemories(characterName: string): Promise<void> {
    return this.request(
      `/v2/chat/memories?character=${encodeURIComponent(characterName)}`,
      { method: "DELETE" }
    );
  }

  // Legacy methods (deprecated - use summary instead)
  async getChatHistory(characterName: string): Promise<ChatMessage[]> {
    // For backward compatibility, this will be removed once summary is fully implemented
    console.warn("getChatHistory is deprecated, use getChatSummary instead");
    return [];
  }

  async clearChatHistory(characterName: string): Promise<void> {
    // For backward compatibility, delegate to clear memories
    return this.clearCharacterMemories(characterName);
  }
}

// Custom Error Class
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Export singleton instance
export const api = new ApiClient(API_BASE_URL);

