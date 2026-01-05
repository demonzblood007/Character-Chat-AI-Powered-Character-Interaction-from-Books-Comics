"use client";

import { motion } from "framer-motion";
import { BookOpen, Sparkles, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui";
import { FloatingBooks } from "./floating-books";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0">
        {/* Main gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-bg-primary via-bg-primary to-bg-secondary" />
        
        {/* Animated orbs */}
        <motion.div
          className="glow-orb w-[600px] h-[600px] -top-40 -left-40 bg-accent-primary/30"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="glow-orb w-[500px] h-[500px] top-1/3 -right-40 bg-accent-secondary/20"
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="glow-orb w-[400px] h-[400px] bottom-20 left-1/4 bg-indigo-500/20"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.2, 0.35, 0.2],
          }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
        />
        
        {/* Grid pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(139, 92, 246, 0.3) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(139, 92, 246, 0.3) 1px, transparent 1px)`,
            backgroundSize: '60px 60px',
          }}
        />
        
        {/* Noise texture */}
        <div className="absolute inset-0 bg-noise" />
      </div>

      {/* Floating books decoration */}
      <FloatingBooks />

      {/* Content */}
      <div className="container-app relative z-10 text-center px-4 py-20">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-primary/10 border border-accent-primary/20 mb-8"
        >
          <Sparkles className="w-4 h-4 text-accent-primary" />
          <span className="text-sm text-accent-primary font-medium">
            Where fiction becomes reality
          </span>
        </motion.div>

        {/* Main heading */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="font-display text-5xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight"
        >
          <span className="block text-text-primary">Chat with</span>
          <span className="block mt-2">
            <span className="text-gradient">Characters</span>
          </span>
          <span className="block text-text-primary mt-2">from Your Books</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="max-w-2xl mx-auto text-lg md:text-xl text-text-secondary mb-12 leading-relaxed"
        >
          Upload your favorite novels, and watch as AI brings every character to life. 
          Have conversations that feel <span className="text-accent-secondary font-medium">real</span>, 
          explore untold stories, and live inside the worlds you love.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 justify-center items-center"
        >
          <Button
            size="lg"
            leftIcon={<BookOpen className="w-5 h-5" />}
            onClick={() => {
              // Will be connected to auth
              const element = document.getElementById("features");
              element?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            Enter Your Story
          </Button>
          <Button
            variant="secondary"
            size="lg"
            leftIcon={<MessageCircle className="w-5 h-5" />}
            onClick={() => {
              const element = document.getElementById("demo");
              element?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            See Demo
          </Button>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-16 flex flex-wrap justify-center gap-8 md:gap-16"
        >
          {[
            { value: "10K+", label: "Characters Created" },
            { value: "50K+", label: "Conversations" },
            { value: "4.9", label: "User Rating" },
          ].map((stat, index) => (
            <div key={index} className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-gradient-warm">
                {stat.value}
              </div>
              <div className="text-sm text-text-muted mt-1">{stat.label}</div>
            </div>
          ))}
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="flex flex-col items-center gap-2 text-text-muted"
          >
            <span className="text-xs uppercase tracking-widest">Scroll</span>
            <div className="w-6 h-10 border-2 border-border rounded-full flex justify-center pt-2">
              <motion.div
                className="w-1 h-2 bg-accent-primary rounded-full"
                animate={{ opacity: [1, 0, 1], y: [0, 12, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              />
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

