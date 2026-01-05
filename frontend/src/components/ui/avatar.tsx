"use client";

import { forwardRef } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { cn, getInitials } from "@/lib/utils";

interface AvatarProps {
  src?: string | null;
  name: string;
  size?: "sm" | "md" | "lg" | "xl" | "2xl";
  className?: string;
  showRing?: boolean;
  ringColor?: "primary" | "secondary" | "success" | "warning";
  status?: "online" | "offline" | "typing";
}

const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  (
    {
      src,
      name,
      size = "md",
      className,
      showRing = false,
      ringColor = "primary",
      status,
    },
    ref
  ) => {
    const sizes = {
      sm: "w-8 h-8 text-xs",
      md: "w-10 h-10 text-sm",
      lg: "w-14 h-14 text-base",
      xl: "w-20 h-20 text-xl",
      "2xl": "w-32 h-32 text-3xl",
    };

    const ringColors = {
      primary: "ring-accent-primary",
      secondary: "ring-accent-secondary",
      success: "ring-green-500",
      warning: "ring-amber-500",
    };

    const statusColors = {
      online: "bg-green-500",
      offline: "bg-gray-500",
      typing: "bg-amber-500",
    };

    return (
      <div ref={ref} className={cn("relative inline-block", className)}>
        <motion.div
          className={cn(
            "relative rounded-full overflow-hidden bg-bg-tertiary flex items-center justify-center font-semibold text-text-primary",
            sizes[size],
            showRing && `ring-2 ring-offset-2 ring-offset-bg-primary ${ringColors[ringColor]}`
          )}
          whileHover={{ scale: 1.05 }}
          transition={{ duration: 0.2 }}
        >
          {src ? (
            <Image
              src={src}
              alt={name}
              fill
              className="object-cover"
              unoptimized
            />
          ) : (
            <span className="font-display">{getInitials(name)}</span>
          )}
        </motion.div>
        
        {/* Status indicator */}
        {status && (
          <motion.div
            className={cn(
              "absolute bottom-0 right-0 rounded-full border-2 border-bg-primary",
              statusColors[status],
              size === "sm" ? "w-2.5 h-2.5" : "w-3.5 h-3.5"
            )}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
          >
            {status === "typing" && (
              <motion.div
                className="w-full h-full rounded-full"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ repeat: Infinity, duration: 1 }}
              />
            )}
          </motion.div>
        )}
      </div>
    );
  }
);

Avatar.displayName = "Avatar";

export { Avatar };

