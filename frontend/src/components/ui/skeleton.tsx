"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
}

function Skeleton({
  className,
  variant = "rectangular",
  width,
  height,
  ...props
}: SkeletonProps) {
  const variants = {
    text: "rounded",
    circular: "rounded-full",
    rectangular: "rounded-xl",
  };

  return (
    <div
      className={cn(
        "skeleton animate-pulse",
        variants[variant],
        className
      )}
      style={{
        width: width,
        height: height || (variant === "text" ? "1em" : undefined),
      }}
      {...props}
    />
  );
}

// Preset skeletons for common use cases
function SkeletonCard() {
  return (
    <div className="bg-bg-secondary rounded-2xl border border-border p-6 space-y-4">
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-4 w-3/4" variant="text" />
      <Skeleton className="h-4 w-1/2" variant="text" />
    </div>
  );
}

function SkeletonAvatar({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizes = {
    sm: "w-8 h-8",
    md: "w-10 h-10",
    lg: "w-14 h-14",
  };
  
  return <Skeleton className={sizes[size]} variant="circular" />;
}

function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-4"
          variant="text"
          width={i === lines - 1 ? "60%" : "100%"}
        />
      ))}
    </div>
  );
}

function SkeletonMessage({ isUser = false }: { isUser?: boolean }) {
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <SkeletonAvatar />
      <div className={cn("flex-1 max-w-[70%] space-y-2", isUser && "items-end")}>
        <Skeleton className="h-20 w-full rounded-2xl" />
      </div>
    </div>
  );
}

export { Skeleton, SkeletonCard, SkeletonAvatar, SkeletonText, SkeletonMessage };

