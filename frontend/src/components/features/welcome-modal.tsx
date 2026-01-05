"use client";

import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Upload, MessageSquare, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui";

interface WelcomeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const steps = [
  {
    icon: Upload,
    title: "Upload Your Books",
    description: "Start by uploading your favorite novels as PDFs. We support any book!",
    color: "text-violet-400",
    bgColor: "bg-violet-500/10",
  },
  {
    icon: Sparkles,
    title: "Discover Characters",
    description: "Our AI will extract every character and understand their unique personalities.",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
  },
  {
    icon: MessageSquare,
    title: "Start Chatting",
    description: "Have real conversations with characters who respond just like in the books!",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
  },
];

export function WelcomeModal({ isOpen, onClose }: WelcomeModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-xl glass-modal rounded-2xl z-50 overflow-hidden"
          >
            {/* Header with gradient */}
            <div className="relative h-32 bg-gradient-to-br from-accent-primary via-indigo-600 to-purple-700 overflow-hidden">
              {/* Pattern overlay */}
              <div className="absolute inset-0 opacity-10">
                <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                  <pattern id="welcome-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
                    <circle cx="20" cy="20" r="2" fill="white" />
                  </pattern>
                  <rect width="100%" height="100%" fill="url(#welcome-pattern)" />
                </svg>
              </div>
              
              {/* Icon */}
              <div className="absolute left-1/2 bottom-0 -translate-x-1/2 translate-y-1/2">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring" }}
                  className="w-20 h-20 rounded-2xl bg-bg-secondary border-4 border-bg-secondary shadow-xl flex items-center justify-center"
                >
                  <BookOpen className="w-10 h-10 text-accent-primary" />
                </motion.div>
              </div>
            </div>

            {/* Content */}
            <div className="pt-14 pb-6 px-8">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-center mb-8"
              >
                <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
                  Welcome to Character Chat! 🎭
                </h2>
                <p className="text-text-secondary">
                  Let's get you started on your journey into the world of stories.
                </p>
              </motion.div>

              {/* Steps */}
              <div className="space-y-4 mb-8">
                {steps.map((step, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + index * 0.1 }}
                    className="flex items-start gap-4 p-4 rounded-xl bg-bg-tertiary/50 hover:bg-bg-tertiary transition-colors"
                  >
                    <div className={`w-12 h-12 rounded-xl ${step.bgColor} flex items-center justify-center flex-shrink-0`}>
                      <step.icon className={`w-6 h-6 ${step.color}`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-text-primary mb-1">
                        {step.title}
                      </h3>
                      <p className="text-sm text-text-secondary">
                        {step.description}
                      </p>
                    </div>
                    <div className="text-text-muted text-sm font-medium flex-shrink-0">
                      {index + 1}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* CTA */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                <Button
                  onClick={onClose}
                  size="lg"
                  className="w-full"
                  rightIcon={<ArrowRight className="w-5 h-5" />}
                >
                  Let's Get Started
                </Button>
              </motion.div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

