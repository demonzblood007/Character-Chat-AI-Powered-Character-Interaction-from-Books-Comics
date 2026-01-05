"use client";

import { motion } from "framer-motion";
import { AnimatedLogo } from "./logo";

interface LoadingScreenProps {
  message?: string;
  submessage?: string;
}

/**
 * Full-page cinematic loading screen
 */
export function LoadingScreen({ 
  message = "Loading your stories...",
  submessage = "Preparing your literary adventure"
}: LoadingScreenProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] bg-bg-primary flex items-center justify-center"
    >
      {/* Background gradient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="glow-orb absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-accent-primary/20" />
        <div className="glow-orb absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-accent-secondary/15" style={{ animationDelay: '2s' }} />
      </div>

      {/* Noise texture */}
      <div className="absolute inset-0 noise-overlay" />

      {/* Content */}
      <div className="relative z-10 text-center">
        <AnimatedLogo className="mb-8" />
        
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="text-text-secondary mb-2"
        >
          {message}
        </motion.p>
        
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="text-text-muted text-sm"
        >
          {submessage}
        </motion.p>

        {/* Loading bar */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: 0.9 }}
          className="mt-8 mx-auto w-48 h-1 bg-bg-tertiary rounded-full overflow-hidden"
        >
          <motion.div
            className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary rounded-full"
            initial={{ x: "-100%" }}
            animate={{ x: "100%" }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        </motion.div>
      </div>
    </motion.div>
  );
}

/**
 * Small loading spinner component
 */
export function LoadingSpinner({ 
  size = "md",
  className = ""
}: { 
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizes = {
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-2",
    lg: "w-12 h-12 border-3",
  };

  return (
    <div className={`${sizes[size]} rounded-full border-accent-primary border-t-transparent animate-spin ${className}`} />
  );
}

/**
 * Processing animation with book icon
 */
export function ProcessingAnimation({ 
  message = "Processing...",
  className = ""
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div className={`flex flex-col items-center gap-4 ${className}`}>
      <div className="relative">
        {/* Rotating ring */}
        <motion.div
          className="w-20 h-20 rounded-full border-2 border-accent-primary/30"
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        />
        
        {/* Pulsing inner circle */}
        <motion.div
          className="absolute inset-2 rounded-full bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center"
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <motion.svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            animate={{ rotateY: [0, 180, 360] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          >
            <path
              d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </motion.svg>
        </motion.div>
      </div>
      
      <p className="text-text-secondary text-sm">{message}</p>
    </div>
  );
}

export default LoadingScreen;

