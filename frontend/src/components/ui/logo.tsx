"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface LogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  variant?: "full" | "icon" | "text";
  animated?: boolean;
  className?: string;
}

const sizes = {
  sm: { icon: 28, text: "text-lg" },
  md: { icon: 36, text: "text-xl" },
  lg: { icon: 48, text: "text-2xl" },
  xl: { icon: 64, text: "text-3xl" },
};

/**
 * Character Chat Logo
 * 
 * Design concept: A book that opens to reveal dialogue/speech
 * - The pages of an open book form a speech bubble shape
 * - Creates a visual metaphor: "stories that speak to you"
 * - Negative space creates the "conversation" element
 * - Gradient adds premium, magical feel
 */
export function Logo({ 
  size = "md", 
  variant = "full", 
  animated = true,
  className 
}: LogoProps) {
  const { icon: iconSize, text: textSize } = sizes[size];

  const LogoIcon = () => (
    <motion.svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      initial={animated ? { scale: 0.8, opacity: 0 } : undefined}
      animate={animated ? { scale: 1, opacity: 1 } : undefined}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex-shrink-0"
    >
      {/* Gradient definitions */}
      <defs>
        <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="50%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id="accentGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      {/* Background circle - subtle */}
      <circle 
        cx="32" 
        cy="32" 
        r="30" 
        fill="url(#logoGradient)"
        opacity="0.15"
      />

      {/* Main icon: Open book that forms a speech bubble */}
      <g filter="url(#glow)">
        {/* Left page - curved to form speech bubble shape */}
        <motion.path
          d="M12 20 C12 16, 16 14, 22 14 L30 14 L30 44 L22 44 C16 44, 12 42, 12 38 Z"
          fill="url(#logoGradient)"
          initial={animated ? { pathLength: 0 } : undefined}
          animate={animated ? { pathLength: 1 } : undefined}
          transition={{ duration: 0.8, delay: 0.2 }}
        />
        
        {/* Right page - curved to form speech bubble shape */}
        <motion.path
          d="M52 20 C52 16, 48 14, 42 14 L34 14 L34 44 L42 44 C48 44, 52 42, 52 38 Z"
          fill="url(#logoGradient)"
          initial={animated ? { pathLength: 0 } : undefined}
          animate={animated ? { pathLength: 1 } : undefined}
          transition={{ duration: 0.8, delay: 0.3 }}
        />

        {/* Center spine - connects the pages */}
        <motion.rect
          x="30"
          y="12"
          width="4"
          height="34"
          rx="2"
          fill="url(#logoGradient)"
          initial={animated ? { scaleY: 0 } : undefined}
          animate={animated ? { scaleY: 1 } : undefined}
          transition={{ duration: 0.5, delay: 0.1 }}
          style={{ transformOrigin: "center top" }}
        />

        {/* Speech bubble tail - the "chat" element */}
        <motion.path
          d="M24 44 L20 52 L28 46 Z"
          fill="url(#accentGradient)"
          initial={animated ? { scale: 0, opacity: 0 } : undefined}
          animate={animated ? { scale: 1, opacity: 1 } : undefined}
          transition={{ duration: 0.4, delay: 0.6 }}
          style={{ transformOrigin: "center" }}
        />
      </g>

      {/* Text lines on pages - representing story content */}
      <motion.g
        initial={animated ? { opacity: 0 } : undefined}
        animate={animated ? { opacity: 1 } : undefined}
        transition={{ duration: 0.4, delay: 0.8 }}
      >
        {/* Left page lines */}
        <rect x="16" y="20" width="10" height="2" rx="1" fill="white" opacity="0.5" />
        <rect x="16" y="26" width="8" height="2" rx="1" fill="white" opacity="0.4" />
        <rect x="16" y="32" width="10" height="2" rx="1" fill="white" opacity="0.3" />
        
        {/* Right page lines */}
        <rect x="38" y="20" width="10" height="2" rx="1" fill="white" opacity="0.5" />
        <rect x="38" y="26" width="8" height="2" rx="1" fill="white" opacity="0.4" />
        <rect x="38" y="32" width="10" height="2" rx="1" fill="white" opacity="0.3" />
      </motion.g>

      {/* Sparkle accent - magical element */}
      <motion.circle
        cx="48"
        cy="16"
        r="3"
        fill="url(#accentGradient)"
        initial={animated ? { scale: 0, opacity: 0 } : undefined}
        animate={animated ? { scale: [0, 1.2, 1], opacity: 1 } : undefined}
        transition={{ duration: 0.6, delay: 1 }}
      />
    </motion.svg>
  );

  const LogoText = () => (
    <motion.div
      className={cn("flex flex-col leading-none", textSize)}
      initial={animated ? { opacity: 0, x: -10 } : undefined}
      animate={animated ? { opacity: 1, x: 0 } : undefined}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <span className="font-display font-semibold tracking-tight text-text-primary">
        Character
      </span>
      <span className="font-display font-light italic text-gradient">
        Chat
      </span>
    </motion.div>
  );

  if (variant === "icon") {
    return (
      <div className={cn("inline-flex", className)}>
        <LogoIcon />
      </div>
    );
  }

  if (variant === "text") {
    return (
      <div className={cn("inline-flex", className)}>
        <LogoText />
      </div>
    );
  }

  return (
    <div className={cn("inline-flex items-center gap-3", className)}>
      <LogoIcon />
      <LogoText />
    </div>
  );
}

/**
 * Animated Logo for special occasions (loading screens, etc.)
 */
export function AnimatedLogo({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn("flex flex-col items-center gap-4", className)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <motion.div
        animate={{ 
          y: [0, -8, 0],
        }}
        transition={{ 
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      >
        <Logo size="xl" variant="icon" animated />
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <Logo size="lg" variant="text" animated={false} />
      </motion.div>
    </motion.div>
  );
}

/**
 * Minimal Logo Mark - just the book-speech icon
 */
export function LogoMark({ 
  size = 32, 
  className 
}: { 
  size?: number; 
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="logoMarkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id="logoMarkAccent" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>
      </defs>
      
      {/* Simplified book-speech icon */}
      <path
        d="M12 18 C12 14, 16 12, 22 12 L30 12 L30 46 L22 46 C16 46, 12 44, 12 40 Z"
        fill="url(#logoMarkGradient)"
      />
      <path
        d="M52 18 C52 14, 48 12, 42 12 L34 12 L34 46 L42 46 C48 46, 52 44, 52 40 Z"
        fill="url(#logoMarkGradient)"
      />
      <rect x="30" y="10" width="4" height="38" rx="2" fill="url(#logoMarkGradient)" />
      <path d="M22 46 L18 54 L26 48 Z" fill="url(#logoMarkAccent)" />
    </svg>
  );
}

export default Logo;

