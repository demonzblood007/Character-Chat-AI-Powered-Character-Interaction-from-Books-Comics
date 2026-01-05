"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { MessageSquare } from "lucide-react";
import Link from "next/link";
import { Avatar } from "@/components/ui";
import { useChatStore } from "@/stores/chat-store";

interface RecentCharacter {
  name: string;
  lastMessage?: string;
  lastActivity: string;
  messageCount: number;
  avatar: string;
}

export default function RecentCharacters() {
  const { getRecentChats } = useChatStore();
  const [characters, setCharacters] = useState<RecentCharacter[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRecentCharacters = () => {
      try {
        console.log("🔄 Fetching recent characters from chat store...");
        // Get recent chats from the chat store
        const recentSessions = getRecentChats();
        console.log("📊 Recent sessions found:", recentSessions.length, recentSessions);

        const recentCharacters: RecentCharacter[] = recentSessions.map(session => {
          const lastMessage = session.messages[session.messages.length - 1];
          console.log(`👤 Character: ${session.characterName}, Messages: ${session.messages.length}, Last: ${lastMessage?.content.substring(0, 30)}...`);
          return {
            name: session.characterName,
            lastMessage: lastMessage?.content.substring(0, 50) + (lastMessage?.content.length > 50 ? "..." : ""),
            lastActivity: session.lastActivity,
            messageCount: session.messages.length,
            avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(session.characterName)}`,
          };
        });

        setCharacters(recentCharacters);
        console.log("✅ Recent characters updated:", recentCharacters.length, recentCharacters.map(c => c.name));
      } catch (error) {
        console.error("❌ Failed to fetch recent characters:", error);
        // Fallback empty state
        setCharacters([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecentCharacters();

    // Update every 30 seconds to show latest activity
    const interval = setInterval(fetchRecentCharacters, 30000);
    return () => clearInterval(interval);
  }, [getRecentChats]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-tertiary">
              <div className="w-10 h-10 rounded-full bg-bg-primary" />
              <div className="flex-1">
                <div className="skeleton h-4 w-3/4 mb-1" />
                <div className="skeleton h-3 w-1/2" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (characters.length === 0) {
    return (
      <div className="text-center py-6">
        <MessageSquare className="w-8 h-8 text-text-muted mx-auto mb-2" />
        <p className="text-sm text-text-muted">
          No recent conversations yet
        </p>
        <p className="text-xs text-text-secondary mt-2">
          Start chatting with characters to see them here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {characters.map((character, index) => (
        <motion.div
          key={character.name}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <Link
            href={`/chat/${encodeURIComponent(character.name)}`}
            className="block p-3 rounded-lg hover:bg-bg-tertiary transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="relative">
                <img
                  src={character.avatar}
                  alt={character.name}
                  className="w-10 h-10 rounded-full object-cover"
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-medium text-text-primary truncate">
                    {character.name}
                  </h4>
                  <span className="text-xs text-text-muted">
                    {character.messageCount} msgs
                  </span>
                </div>
                {character.lastMessage && (
                  <p className="text-sm text-text-secondary truncate">
                    {character.lastMessage}
                  </p>
                )}
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-xs text-text-muted">
                    {new Date(character.lastActivity).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                </div>
              </div>
            </div>
          </Link>
        </motion.div>
      ))}
    </div>
  );
}

