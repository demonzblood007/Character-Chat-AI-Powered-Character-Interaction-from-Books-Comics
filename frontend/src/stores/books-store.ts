/**
 * Books/Files State Store
 */

import { create } from "zustand";
import { BookFile, Character, api } from "@/lib/api";

interface BooksState {
  // State
  books: BookFile[];
  currentBook: BookFile | null;
  characters: Character[];
  isLoading: boolean;
  uploadProgress: number;
  error: string | null;
  
  // Actions
  setBooks: (books: BookFile[]) => void;
  setCurrentBook: (book: BookFile | null) => void;
  setCharacters: (characters: Character[]) => void;
  setLoading: (loading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setError: (error: string | null) => void;
  
  // API Actions
  fetchBooks: () => Promise<void>;
  uploadBook: (file: File) => Promise<BookFile>;
  fetchBookStatus: (bookId: string) => Promise<BookFile>;
  fetchCharacters: (bookId: string) => Promise<void>;
  pollBookStatus: (bookId: string, interval?: number) => () => void;
  deleteBook: (bookId: string) => Promise<{
    ok: boolean;
    deleted_file_id: string;
    deleted_chat_sessions?: number;
    deleted_memories?: number;
    deleted_entities?: number;
    deleted_qdrant_chunks?: number;
    deleted_qdrant_memories?: number;
    character_names?: string[];
  }>;
}

export const useBooksStore = create<BooksState>((set, get) => ({
  books: [],
  currentBook: null,
  characters: [],
  isLoading: false,
  uploadProgress: 0,
  error: null,

  setBooks: (books) => set({ books }),
  setCurrentBook: (book) => set({ currentBook: book }),
  setCharacters: (characters) => set({ characters }),
  setLoading: (loading) => set({ isLoading: loading }),
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  setError: (error) => set({ error }),

  fetchBooks: async () => {
    set({ isLoading: true, error: null });
    try {
      console.log("📚 Fetching books...");

      // Check authentication first
      const { useAuthStore } = await import("@/stores/auth-store");
      const authStore = useAuthStore.getState();
      console.log("🔐 Auth state:", {
        isAuthenticated: authStore.isAuthenticated,
        hasUser: !!authStore.user,
        isLoading: authStore.isLoading
      });

      const books = await api.getFiles();
      console.log("✅ Books fetched:", books);
      set({ books, error: null });
    } catch (error) {
      console.error("❌ Failed to fetch books:", error);

      // Better error message extraction
      let errorMessage = "Failed to fetch books. Please try again.";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'object' && error !== null) {
        errorMessage = (error as any).message || (error as any).detail || JSON.stringify(error);
      }

      set({ error: errorMessage, books: [] });
    } finally {
      set({ isLoading: false });
    }
  },

  uploadBook: async (file) => {
    set({ isLoading: true, uploadProgress: 0 });
    try {
      const book = await api.uploadFile(file, (progress) => {
        set({ uploadProgress: progress });
      });
      
      // Add to books list
      set((state) => ({ 
        books: [book, ...state.books],
        uploadProgress: 100 
      }));
      
      return book;
    } catch (error) {
      console.error("Failed to upload book:", error);
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  fetchBookStatus: async (bookId) => {
    try {
      const book = await api.getFileStatus(bookId);
      
      // Update in books list
      set((state) => ({
        books: state.books.map((b) => 
          b.id === bookId ? book : b
        ),
        currentBook: state.currentBook?.id === bookId ? book : state.currentBook,
      }));
      
      return book;
    } catch (error) {
      console.error("Failed to fetch book status:", error);
      throw error;
    }
  },

  fetchCharacters: async (bookId) => {
    set({ isLoading: true, error: null });
    try {
      console.log("👥 Fetching characters for book:", bookId);
      const characters = await api.getCharacters(bookId);
      console.log("✅ Characters fetched:", characters);
      set({ characters, error: null });
    } catch (error) {
      console.error("❌ Failed to fetch characters:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to fetch characters. Please try again.";
      set({ error: errorMessage, characters: [] });
    } finally {
      set({ isLoading: false });
    }
  },

  pollBookStatus: (bookId, interval = 3000) => {
    const poll = async () => {
      const book = await get().fetchBookStatus(bookId);
      if (book.status === "done" || book.status === "failed") {
        clearInterval(pollInterval);
      }
    };

    const pollInterval = setInterval(poll, interval);
    poll(); // Initial fetch

    return () => clearInterval(pollInterval);
  },

  deleteBook: async (bookId) => {
    console.log("🗑️ Deleting book:", bookId);
    set({ isLoading: true });

    try {
      const result = await api.deleteFile(bookId);
      console.log("✅ Book deleted successfully:", result);

      // Remove the book from the local state
      set((state) => ({
        books: state.books.filter(book => book.id !== bookId),
        currentBook: state.currentBook?.id === bookId ? null : state.currentBook,
      }));

      return result;
    } catch (error) {
      console.error("❌ Failed to delete book:", error);

      // Re-throw with better error message
      if (error instanceof Error) {
        throw error;
      } else if (typeof error === 'object' && error !== null) {
        const errorMessage = (error as any).message || (error as any).detail || JSON.stringify(error);
        throw new Error(errorMessage);
      } else {
        throw new Error(String(error));
      }
    } finally {
      set({ isLoading: false });
    }
  },
}));

