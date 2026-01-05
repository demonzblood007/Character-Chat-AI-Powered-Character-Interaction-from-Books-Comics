"use client";

import { useEffect, useState, useRef, use } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import {
  Send,
  ArrowLeft,
  MoreVertical,
  Trash2,
  Download,
  Info,
  Sparkles,
  Menu,
  X,
  BookOpen,
  MessageCircle,
  Heart,
  Bookmark,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { Button, Avatar, Input } from "@/components/ui";
import { useChatStore } from "@/stores/chat-store";
import { api, Character } from "@/lib/api";
import { ChatMessage } from "@/components/features/chat-message";
import { ChatSidebar } from "@/components/features/chat-sidebar";
import { TypingIndicator } from "@/components/features/typing-indicator";

interface PageProps {
  params: Promise<{ character: string }>;
}

// Atmospheric background images for chat
const CHAT_BACKGROUNDS = [
  "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1920&q=80",
  "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1920&q=80",
];

// Conversation starters based on character type
const CONVERSATION_STARTERS = [
  { text: "Tell me about yourself", icon: "👋" },
  { text: "What's your greatest challenge?", icon: "⚡" },
  { text: "What motivates you?", icon: "💫" },
  { text: "Tell me about your world", icon: "🌍" },
];

export default function ChatPage({ params }: PageProps) {
  const { character: characterName } = use(params);
  const decodedName = decodeURIComponent(characterName);

  const {
    currentCharacter,
    currentSession,
    isTyping,
    streamingContent,
    statusMessage,
    error,
    setCharacter,
    sendMessage,
    clearCurrentChat,
    getCharacterMessages,
    setError,
    clearError,
  } = useChatStore();

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Get messages for current character
  const messages = getCharacterMessages(decodedName);

  // Load character data
  useEffect(() => {
    const loadCharacter = async () => {
      try {
        clearError(); // Clear any previous errors
        const char = await api.getCharacter(decodedName);
        setCharacter(char);
      } catch (error) {
        console.error("Failed to load character:", error);

        // Better error message extraction
        let errorMessage = "Unknown error occurred";
        if (error instanceof Error) {
          errorMessage = error.message;
        } else if (typeof error === 'object' && error !== null) {
          // Handle API error objects
          errorMessage = (error as any).message || (error as any).detail || JSON.stringify(error);
        } else {
          errorMessage = String(error);
        }

        console.error("Character loading error details:", errorMessage);

        // Create fallback character
        const demoChar: Character = {
          name: decodedName,
          description: "A fascinating character from your favorite book, ready to have meaningful conversations with you.",
          powers: ["Wisdom", "Courage", "Wit"],
          story_arcs: ["The Beginning", "The Journey", "The Resolution"],
          avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(decodedName)}`,
          relationships: [],
        };
        setCharacter(demoChar);
        setError(`Character details not available: ${errorMessage}. You can still chat!`);
      } finally {
        setIsLoading(false);
      }
    };

    loadCharacter();
  }, [decodedName, setCharacter, setError, clearError]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, [isLoading]);

  const handleSend = async () => {
    if (!inputValue.trim() || isTyping) return;

    const message = inputValue.trim();
    setInputValue("");
    
    try {
      await sendMessage(message);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = async () => {
    if (confirm("Are you sure you want to clear this conversation? This will remove all messages but keep the session.")) {
      try {
        clearCurrentChat();
        setShowMenu(false);
      } catch (error) {
        console.error("Failed to clear chat:", error);
        setError("Failed to clear chat. Please try again.");
      }
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-accent-primary to-purple-600 animate-pulse" />
            <div className="absolute inset-2 rounded-full bg-bg-primary flex items-center justify-center">
              <MessageCircle className="w-10 h-10 text-accent-primary animate-bounce" />
            </div>
          </div>
          <p className="font-display text-xl text-text-primary mb-2">Summoning {decodedName}</p>
          <p className="text-text-muted text-sm">Preparing your conversation...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary flex relative">
      {/* Atmospheric Background */}
      <div className="fixed inset-0 pointer-events-none">
        <Image
          src={CHAT_BACKGROUNDS[0]}
          alt="Atmosphere"
          fill
          className="object-cover opacity-[0.03]"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-bg-primary via-transparent to-bg-primary" />
      </div>

      {/* Sidebar - Chat History */}
      <ChatSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        characterName={decodedName}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-screen relative z-10">
        {/* Header - Glass effect */}
        <header className="flex-shrink-0 glass-strong border-b border-border">
          <div className="flex items-center justify-between px-4 md:px-6 h-18 py-3">
            {/* Left side */}
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                className="lg:hidden"
                onClick={() => setIsSidebarOpen(true)}
              >
                <Menu className="w-5 h-5" />
              </Button>
              
              <Link href="/dashboard">
                <button className="btn-ghost p-2 rounded-xl">
                  <ArrowLeft className="w-5 h-5" />
                </button>
              </Link>

              {/* Character info */}
              <div className="flex items-center gap-4">
                <div className="avatar-ring">
                  <Image
                    src={currentCharacter?.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(decodedName)}`}
                    alt={currentCharacter?.name || decodedName}
                    width={48}
                    height={48}
                    className="rounded-full"
                  />
                </div>
                <div>
                  <h1 className="font-display text-lg font-medium text-text-primary">
                    {currentCharacter?.name || decodedName}
                  </h1>
                  <p className="text-xs text-accent-primary flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
                    In character • Ready
                  </p>
                </div>
              </div>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setIsFavorite(!isFavorite)}
                className={`p-2.5 rounded-xl transition-all ${isFavorite ? 'bg-rose-500/20 text-rose-400' : 'hover:bg-bg-tertiary text-text-muted'}`}
              >
                <Heart className={`w-5 h-5 ${isFavorite ? 'fill-current' : ''}`} />
              </button>
              
              <Link href={`/character/${encodeURIComponent(decodedName)}`}>
                <button className="p-2.5 rounded-xl hover:bg-bg-tertiary text-text-muted transition-all">
                  <Info className="w-5 h-5" />
                </button>
              </Link>

              {/* Menu */}
              <div className="relative">
                <button
                  className="p-2.5 rounded-xl hover:bg-bg-tertiary text-text-muted transition-all"
                  onClick={() => setShowMenu(!showMenu)}
                >
                  <MoreVertical className="w-5 h-5" />
                </button>

                <AnimatePresence>
                  {showMenu && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setShowMenu(false)}
                      />
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute right-0 mt-2 w-52 glass-strong rounded-2xl shadow-2xl overflow-hidden z-50"
                      >
                        <button
                          onClick={() => {
                            setShowMenu(false);
                          }}
                          className="w-full flex items-center gap-3 px-4 py-3.5 text-text-secondary hover:bg-bg-tertiary transition-colors"
                        >
                          <Bookmark className="w-4 h-4" />
                          <span>Save Conversation</span>
                        </button>
                        <button
                          onClick={() => {
                            setShowMenu(false);
                          }}
                          className="w-full flex items-center gap-3 px-4 py-3.5 text-text-secondary hover:bg-bg-tertiary transition-colors"
                        >
                          <Download className="w-4 h-4" />
                          <span>Export Chat</span>
                        </button>
                        <hr className="border-border" />
                        <div className="w-full flex items-center gap-3 px-4 py-3.5 text-text-secondary">
                          <Info className="w-4 h-4" />
                          <div className="flex-1">
                            <span className="text-sm font-medium">Character Info</span>
                            {currentCharacter && (
                              <div className="text-xs text-text-muted mt-1">
                                {currentCharacter.description.substring(0, 60)}...
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="w-full flex items-center gap-3 px-4 py-3.5 text-text-secondary">
                          <TrendingUp className="w-4 h-4" />
                          <div className="flex-1">
                            <span className="text-sm font-medium">Session Stats</span>
                            {currentSession && (
                              <div className="text-xs text-text-muted mt-1">
                                {currentSession.messages.length} messages • {currentSession.memoriesUsed} memories • {currentSession.tokensUsed} tokens
                              </div>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={handleClearChat}
                          className="w-full flex items-center gap-3 px-4 py-3.5 text-rose-400 hover:bg-rose-500/10 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                          <span>Clear Memories</span>
                        </button>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto scrollbar-hide">
          <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
            {/* Empty state - Beautiful intro */}
            {messages.length === 0 && !isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                {/* Character Portrait */}
                <motion.div
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                  className="relative inline-block mb-8"
                >
                  <div className="absolute inset-0 scale-110 bg-gradient-to-r from-accent-primary to-purple-600 rounded-full blur-xl opacity-30" />
                  <div className="avatar-ring p-1">
                    <Image
                      src={currentCharacter?.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(decodedName)}`}
                      alt={currentCharacter?.name || decodedName}
                      width={120}
                      height={120}
                      className="rounded-full"
                    />
                  </div>
                </motion.div>
                
                <h2 className="font-display text-3xl font-light text-text-primary mb-3">
                  Meet <span className="text-gradient italic font-medium">{currentCharacter?.name || decodedName}</span>
                </h2>
                <p className="font-literary text-text-secondary max-w-lg mx-auto mb-10 text-lg italic leading-relaxed">
                  "{currentCharacter?.description || "I'm ready to share my story with you. Ask me anything about my adventures, thoughts, or the world I come from."}"
                </p>
                
                {/* Conversation starters */}
                <div className="space-y-3">
                  <p className="text-text-muted text-sm uppercase tracking-wider mb-4">Start the conversation</p>
                  <div className="flex flex-wrap justify-center gap-3">
                    {CONVERSATION_STARTERS.map((starter) => (
                      <motion.button
                        key={starter.text}
                        onClick={() => setInputValue(starter.text)}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="px-5 py-3 rounded-2xl bg-bg-secondary border border-border text-text-secondary hover:text-text-primary hover:border-accent-primary/50 hover:bg-bg-tertiary transition-all text-sm flex items-center gap-2"
                      >
                        <span>{starter.icon}</span>
                        {starter.text}
                      </motion.button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Messages */}
            <AnimatePresence mode="popLayout">
              {messages.map((message, index) => (
                <ChatMessage
                  key={`${message.timestamp}-${index}`}
                  message={message}
                  character={currentCharacter}
                  isLatest={index === messages.length - 1 && !isTyping}
                />
              ))}
            </AnimatePresence>

            {/* Typing indicator / Streaming content */}
            {(isTyping || streamingContent) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4"
              >
                <div className="flex-shrink-0">
                  <div className="avatar-ring p-0.5">
                    <Image
                      src={currentCharacter?.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(decodedName)}`}
                      alt={currentCharacter?.name || decodedName}
                      width={44}
                      height={44}
                      className="rounded-full"
                    />
                  </div>
                </div>
                <div className="flex-1 max-w-[85%]">
                  {statusMessage && (
                    <motion.p 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-xs text-accent-primary mb-2 flex items-center gap-2"
                    >
                      <Sparkles className="w-3 h-3 animate-pulse" />
                      {statusMessage}
                    </motion.p>
                  )}
                  <div className="chat-bubble-assistant px-5 py-4">
                    {streamingContent ? (
                      <p className="font-literary text-text-primary leading-relaxed whitespace-pre-wrap">
                        {streamingContent}
                        <motion.span
                          animate={{ opacity: [1, 0, 1] }}
                          transition={{ duration: 0.8, repeat: Infinity }}
                          className="text-accent-primary ml-0.5"
                        >
                          |
                        </motion.span>
                      </p>
                    ) : (
                      <TypingIndicator />
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area - Premium Design */}
        <div className="flex-shrink-0 border-t border-border glass-strong">
          <div className="max-w-3xl mx-auto px-4 py-5">
            <div className="relative">
              <div className="flex items-end gap-3">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={`Message ${currentCharacter?.name || decodedName}...`}
                    disabled={isTyping}
                    className="w-full bg-bg-secondary border border-border rounded-2xl px-5 py-4 pr-14 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary/50 focus:ring-2 focus:ring-accent-primary/20 transition-all"
                  />
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isTyping}
                  className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                    inputValue.trim() && !isTyping
                      ? 'bg-gradient-to-r from-accent-primary to-purple-600 text-white shadow-lg shadow-accent-primary/30'
                      : 'bg-bg-tertiary text-text-muted'
                  }`}
                >
                  <Send className="w-5 h-5" />
                </motion.button>
              </div>
            </div>
            <p className="text-xs text-text-muted text-center mt-4 flex items-center justify-center gap-2">
              <BookOpen className="w-3 h-3" />
              Responses reflect the character's personality from the book
              <Sparkles className="w-3 h-3 text-accent-primary" />
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
