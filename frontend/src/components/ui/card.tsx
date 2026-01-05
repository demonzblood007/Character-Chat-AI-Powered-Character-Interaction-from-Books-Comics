"use client";

import { forwardRef } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

interface CardProps extends Omit<HTMLMotionProps<"div">, "children"> {
  variant?: "default" | "elevated" | "glass";
  hover?: boolean;
  glow?: boolean;
  children?: React.ReactNode;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", hover = true, glow = false, children, ...props }, ref) => {
    const variants = {
      default: "bg-bg-secondary border-border",
      elevated: "bg-bg-tertiary border-border-light",
      glass: "bg-bg-secondary/60 backdrop-blur-xl border-border/50",
    };

    return (
      <motion.div
        ref={ref}
        className={cn(
          "relative rounded-2xl border p-6 transition-all duration-300",
          variants[variant],
          hover && "hover:border-accent-primary/50 cursor-pointer",
          glow && "hover:shadow-[0_0_40px_rgba(139,92,246,0.15)]",
          className
        )}
        whileHover={hover ? { 
          y: -4, 
          scale: 1.01,
          transition: { duration: 0.2, ease: "easeOut" } 
        } : undefined}
        {...props}
      >
        {/* Subtle gradient overlay on hover */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent-primary/5 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
        <div className="relative z-10">{children}</div>
      </motion.div>
    );
  }
);

Card.displayName = "Card";

// Card Header
interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-2 mb-4", className)}
      {...props}
    />
  )
);

CardHeader.displayName = "CardHeader";

// Card Title
interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn("font-display text-xl font-semibold text-text-primary", className)}
      {...props}
    />
  )
);

CardTitle.displayName = "CardTitle";

// Card Description
interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("text-sm text-text-secondary", className)}
      {...props}
    />
  )
);

CardDescription.displayName = "CardDescription";

// Card Content
interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("", className)} {...props} />
  )
);

CardContent.displayName = "CardContent";

export { Card, CardHeader, CardTitle, CardDescription, CardContent };

