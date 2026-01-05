"use client";

import { motion } from "framer-motion";
import { Avatar } from "@/components/ui";
import { ChatMessage as ChatMessageType, Character } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

interface ChatMessageProps {
  message: ChatMessageType;
  character: Character | null;
  isLatest?: boolean;
}

export function ChatMessage({ message, character, isLatest }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      {/* Avatar */}
      {!isUser && (
        <Avatar
          src={character?.avatar}
          name={character?.name || "Character"}
          size="md"
        />
      )}

      {/* Message bubble */}
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[80%]`}>
        {/* Character name (for assistant messages) */}
        {!isUser && character && (
          <span className="text-xs text-accent-primary font-medium mb-1 ml-1">
            {character.name}
          </span>
        )}

        <div
          className={`relative px-5 py-4 ${
            isUser
              ? "bg-gradient-to-br from-accent-primary to-indigo-600 text-white rounded-2xl rounded-tr-sm"
              : "bg-bg-secondary text-text-primary rounded-2xl rounded-tl-sm"
          }`}
        >
          {/* Message content */}
          <p className={`leading-relaxed ${!isUser ? "font-literary" : ""}`}>
            {!isUser && '"'}
            {message.content}
            {!isUser && '"'}
          </p>

          {/* Subtle glow for assistant messages */}
          {!isUser && isLatest && (
            <motion.div
              className="absolute inset-0 rounded-2xl rounded-tl-sm bg-accent-primary/10"
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 0 }}
              transition={{ duration: 2 }}
            />
          )}
        </div>

        {/* Timestamp */}
        <span className="text-xs text-text-muted mt-1 mx-1">
          {formatRelativeTime(message.timestamp)}
        </span>
      </div>
    </motion.div>
  );
}

