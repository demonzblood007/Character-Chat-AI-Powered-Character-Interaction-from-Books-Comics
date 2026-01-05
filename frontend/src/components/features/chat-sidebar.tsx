"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, MessageSquare, Clock, Search } from "lucide-react";
import { Button, Input } from "@/components/ui";
import { useState } from "react";

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  characterName: string;
}

// Demo chat history
const chatHistory = [
  { id: "1", preview: "Tell me about yourself", date: "Today" },
  { id: "2", preview: "What's your greatest challenge?", date: "Yesterday" },
  { id: "3", preview: "How did you become who you are?", date: "2 days ago" },
  { id: "4", preview: "What do you think about friendship?", date: "Last week" },
];

export function ChatSidebar({ isOpen, onClose, characterName }: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredHistory = chatHistory.filter((chat) =>
    chat.preview.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:flex flex-col w-80 border-r border-border bg-bg-secondary h-screen">
        <div className="p-4 border-b border-border">
          <h2 className="font-display font-semibold text-text-primary flex items-center gap-2">
            <Clock className="w-5 h-5 text-accent-primary" />
            Chat History
          </h2>
        </div>

        {/* Search */}
        <div className="p-4">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            leftIcon={<Search className="w-4 h-4" />}
          />
        </div>

        {/* History list */}
        <div className="flex-1 overflow-y-auto scrollbar-hide">
          <div className="p-2 space-y-1">
            {filteredHistory.length > 0 ? (
              filteredHistory.map((chat) => (
                <button
                  key={chat.id}
                  className="w-full text-left p-3 rounded-xl hover:bg-bg-tertiary transition-colors group"
                >
                  <div className="flex items-start gap-3">
                    <MessageSquare className="w-4 h-4 text-text-muted mt-0.5 group-hover:text-accent-primary transition-colors" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text-primary truncate group-hover:text-accent-primary transition-colors">
                        {chat.preview}
                      </p>
                      <p className="text-xs text-text-muted mt-1">
                        {chat.date}
                      </p>
                    </div>
                  </div>
                </button>
              ))
            ) : (
              <div className="text-center py-8">
                <MessageSquare className="w-8 h-8 text-text-muted mx-auto mb-2" />
                <p className="text-sm text-text-muted">No conversations found</p>
              </div>
            )}
          </div>
        </div>

        {/* New chat button */}
        <div className="p-4 border-t border-border">
          <Button variant="secondary" className="w-full">
            <MessageSquare className="w-4 h-4 mr-2" />
            New Conversation
          </Button>
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
              onClick={onClose}
            />

            {/* Sidebar panel */}
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 bottom-0 w-80 bg-bg-secondary border-r border-border z-50 lg:hidden flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-border">
                <h2 className="font-display font-semibold text-text-primary flex items-center gap-2">
                  <Clock className="w-5 h-5 text-accent-primary" />
                  Chat History
                </h2>
                <Button variant="ghost" size="sm" onClick={onClose}>
                  <X className="w-5 h-5" />
                </Button>
              </div>

              {/* Search */}
              <div className="p-4">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search conversations..."
                  leftIcon={<Search className="w-4 h-4" />}
                />
              </div>

              {/* History list */}
              <div className="flex-1 overflow-y-auto scrollbar-hide">
                <div className="p-2 space-y-1">
                  {filteredHistory.map((chat) => (
                    <button
                      key={chat.id}
                      onClick={onClose}
                      className="w-full text-left p-3 rounded-xl hover:bg-bg-tertiary transition-colors group"
                    >
                      <div className="flex items-start gap-3">
                        <MessageSquare className="w-4 h-4 text-text-muted mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-text-primary truncate">
                            {chat.preview}
                          </p>
                          <p className="text-xs text-text-muted mt-1">
                            {chat.date}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

