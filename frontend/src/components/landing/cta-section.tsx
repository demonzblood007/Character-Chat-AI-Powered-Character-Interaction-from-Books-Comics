"use client";

import { motion } from "framer-motion";
import { ArrowRight, BookOpen, Star } from "lucide-react";
import { Button } from "@/components/ui";

export function CTASection() {
  return (
    <section className="py-32 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-bg-secondary to-bg-primary" />
      
      {/* Animated gradient orbs */}
      <motion.div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)",
        }}
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.5, 0.7, 0.5],
        }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      />
      
      {/* Stars decoration */}
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: [0.2, 0.6, 0.2], scale: 1 }}
          transition={{
            duration: 2 + Math.random() * 2,
            repeat: Infinity,
            delay: Math.random() * 2,
          }}
        >
          <Star className="w-3 h-3 text-accent-secondary/30 fill-accent-secondary/30" />
        </motion.div>
      ))}

      <div className="container-app relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl mx-auto text-center"
        >
          {/* Icon */}
          <motion.div
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ type: "spring", stiffness: 200, damping: 15 }}
            className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-gradient-to-br from-accent-primary to-indigo-600 flex items-center justify-center shadow-lg shadow-accent-primary/30"
          >
            <BookOpen className="w-10 h-10 text-white" />
          </motion.div>

          {/* Heading */}
          <h2 className="font-display text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
            Ready to{" "}
            <span className="text-gradient">Enter Your Story</span>?
          </h2>
          
          <p className="text-lg md:text-xl text-text-secondary mb-10 max-w-2xl mx-auto">
            Join thousands of readers who've discovered a new way to experience 
            their favorite books. Your characters are waiting.
          </p>

          {/* CTA Button */}
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Button
              size="lg"
              rightIcon={<ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />}
              className="group text-lg px-10 py-5"
            >
              Start Free — No Credit Card
            </Button>
          </motion.div>

          {/* Trust badges */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="mt-12 flex flex-wrap justify-center items-center gap-8 text-text-muted text-sm"
          >
            <div className="flex items-center gap-2">
              <div className="flex -space-x-2">
                {["A", "B", "C", "D"].map((letter, i) => (
                  <div
                    key={i}
                    className="w-8 h-8 rounded-full bg-bg-tertiary border-2 border-bg-primary flex items-center justify-center text-xs font-medium text-text-primary"
                  >
                    {letter}
                  </div>
                ))}
              </div>
              <span>1,000+ readers this week</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className="w-4 h-4 text-accent-secondary fill-accent-secondary"
                  />
                ))}
              </div>
              <span>4.9/5 average rating</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

