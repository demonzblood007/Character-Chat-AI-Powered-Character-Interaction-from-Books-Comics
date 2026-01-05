/**
 * Utility Functions
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Merge Tailwind classes intelligently
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format relative time
export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const past = new Date(date);
  const diffMs = now.getTime() - past.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  
  return past.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// Truncate text with ellipsis
export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length).trim() + "...";
}

// Generate initials from name
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((word) => word[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

// Delay utility for animations
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Generate DiceBear avatar URL
export function generateAvatar(seed: string): string {
  return `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(seed)}`;
}

// Format file size
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// Get status color
export function getStatusColor(status: string): string {
  switch (status) {
    case "done":
      return "text-green-400";
    case "processing":
    case "extracting_characters":
    case "extracting_relationships":
      return "text-amber-400";
    case "queued":
      return "text-blue-400";
    case "failed":
      return "text-red-400";
    default:
      return "text-text-secondary";
  }
}

// Get status label
export function getStatusLabel(status: string): string {
  switch (status) {
    case "done":
      return "Ready";
    case "processing":
      return "Processing...";
    case "extracting_characters":
      return "Discovering characters...";
    case "extracting_relationships":
      return "Mapping relationships...";
    case "queued":
      return "In queue";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

// Relationship type to color
export function getRelationshipColor(type: string): string {
  switch (type) {
    case "ally":
    case "friend":
      return "#22c55e"; // green
    case "enemy":
      return "#ef4444"; // red
    case "family":
      return "#8b5cf6"; // purple
    case "lover":
      return "#ec4899"; // pink
    default:
      return "#71717a"; // gray
  }
}

