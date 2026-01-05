"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles } from "lucide-react";
import { Avatar, Button } from "@/components/ui";

const demoConversation = [
  {
    role: "user",
    content: "What drives you to fight crime in Gotham, despite all the dangers?",
  },
  {
    role: "assistant",
    character: "Batman",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Batman&backgroundColor=1a1a24",
    content: "Every night I step into the darkness, I see my parents' faces. Not as they died, but as they lived — full of hope for this city. Gotham doesn't need a hero who's invincible. It needs one who understands loss, who's willing to become something more than human to prevent others from experiencing that same pain. The danger doesn't matter. What matters is the eight-year-old boy who can walk home safely tonight because someone chose to stand between him and the shadows.",
  },
];

export function DemoChat() {
  const [messages, setMessages] = useState<typeof demoConversation>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [displayedContent, setDisplayedContent] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  // Simulate conversation
  useEffect(() => {
    if (currentIndex >= demoConversation.length) return;

    const message = demoConversation[currentIndex];
    
    if (message.role === "user") {
      // Show user message immediately
      setMessages((prev) => [...prev, message]);
      setCurrentIndex((prev) => prev + 1);
    } else {
      // Simulate typing for assistant
      setIsTyping(true);
      setDisplayedContent("");
      
      // Start typing after a delay
      const typeDelay = setTimeout(() => {
        setIsTyping(false);
        let charIndex = 0;
        
        const typeInterval = setInterval(() => {
          if (charIndex < message.content.length) {
            setDisplayedContent(message.content.slice(0, charIndex + 1));
            charIndex++;
          } else {
            clearInterval(typeInterval);
            setMessages((prev) => [...prev, message]);
            setDisplayedContent("");
            setCurrentIndex((prev) => prev + 1);
          }
        }, 20); // Typing speed

        return () => clearInterval(typeInterval);
      }, 1500);

      return () => clearTimeout(typeDelay);
    }
  }, [currentIndex]);

  // Reset and replay demo
  const replayDemo = () => {
    setMessages([]);
    setCurrentIndex(0);
    setDisplayedContent("");
    setIsTyping(false);
  };

  return (
    <section id="demo" className="py-32 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-bg-secondary via-bg-primary to-bg-secondary" />
      
      {/* Glow effects */}
      <div className="absolute top-1/2 left-0 w-[500px] h-[500px] bg-accent-secondary/10 blur-[150px] rounded-full -translate-y-1/2" />
      <div className="absolute top-1/2 right-0 w-[500px] h-[500px] bg-accent-primary/10 blur-[150px] rounded-full -translate-y-1/2" />

      <div className="container-app relative z-10">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-accent-secondary font-medium text-sm uppercase tracking-widest">
            Live Demo
          </span>
          <h2 className="font-display text-4xl md:text-5xl font-bold mt-4 mb-6">
            Experience the{" "}
            <span className="text-gradient-warm">Magic</span>
          </h2>
          <p className="text-text-secondary text-lg max-w-2xl mx-auto">
            Watch how Batman responds to your questions, staying true to his 
            character while engaging in meaningful dialogue.
          </p>
        </motion.div>

        {/* Chat demo container */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="max-w-3xl mx-auto"
        >
          <div className="bg-bg-secondary/80 backdrop-blur-xl rounded-3xl border border-border overflow-hidden shadow-2xl">
            {/* Chat header */}
            <div className="flex items-center gap-4 px-6 py-4 border-b border-border bg-bg-tertiary/50">
              <Avatar
                src="https://api.dicebear.com/7.x/avataaars/svg?seed=Batman&backgroundColor=1a1a24"
                name="Batman"
                size="lg"
                status="online"
              />
              <div>
                <h4 className="font-display font-semibold text-text-primary">Batman</h4>
                <p className="text-sm text-text-muted">The Dark Knight • Gotham City</p>
              </div>
              <div className="ml-auto">
                <Sparkles className="w-5 h-5 text-accent-primary animate-pulse" />
              </div>
            </div>

            {/* Messages area */}
            <div className="p-6 min-h-[400px] flex flex-col gap-6">
              <AnimatePresence mode="popLayout">
                {messages.map((message, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                    className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
                  >
                    {message.role === "assistant" && (
                      <Avatar
                        src={message.avatar}
                        name={message.character || "Assistant"}
                        size="md"
                      />
                    )}
                    <div
                      className={`max-w-[80%] rounded-2xl px-5 py-4 ${
                        message.role === "user"
                          ? "bg-accent-primary text-white rounded-tr-sm"
                          : "bg-bg-tertiary text-text-primary rounded-tl-sm"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <p className="font-literary text-[15px] leading-relaxed italic">
                          "{message.content}"
                        </p>
                      ) : (
                        <p className="text-[15px] leading-relaxed">{message.content}</p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Typing indicator or streaming content */}
              {(isTyping || displayedContent) && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <Avatar
                    src="https://api.dicebear.com/7.x/avataaars/svg?seed=Batman&backgroundColor=1a1a24"
                    name="Batman"
                    size="md"
                    status="typing"
                  />
                  <div className="bg-bg-tertiary rounded-2xl rounded-tl-sm px-5 py-4 max-w-[80%]">
                    {isTyping ? (
                      <div className="flex gap-1.5">
                        {[0, 1, 2].map((i) => (
                          <motion.div
                            key={i}
                            className="w-2 h-2 bg-accent-primary rounded-full"
                            animate={{ y: [0, -6, 0] }}
                            transition={{
                              duration: 0.6,
                              repeat: Infinity,
                              delay: i * 0.15,
                            }}
                          />
                        ))}
                      </div>
                    ) : (
                      <p className="font-literary text-[15px] leading-relaxed italic text-text-primary">
                        "{displayedContent}
                        <motion.span
                          animate={{ opacity: [1, 0, 1] }}
                          transition={{ duration: 0.8, repeat: Infinity }}
                          className="text-accent-primary"
                        >
                          |
                        </motion.span>
                        "
                      </p>
                    )}
                  </div>
                </motion.div>
              )}
            </div>

            {/* Input area (decorative for demo) */}
            <div className="px-6 py-4 border-t border-border bg-bg-tertiary/30">
              <div className="flex gap-3">
                <div className="flex-1 bg-bg-tertiary rounded-xl px-4 py-3 text-text-muted border border-border">
                  Type your message...
                </div>
                <Button
                  size="md"
                  className="rounded-xl"
                  onClick={replayDemo}
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </div>

          {/* Replay button */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="text-center mt-8"
          >
            <Button
              variant="ghost"
              size="sm"
              onClick={replayDemo}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              Replay Demo
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

