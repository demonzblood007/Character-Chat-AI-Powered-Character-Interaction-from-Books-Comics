"use client";

import { motion } from "framer-motion";
import { BookOpen, Clock, Users, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import { BookFile } from "@/lib/api";
import { getStatusColor, getStatusLabel, formatRelativeTime } from "@/lib/utils";

interface BookCardProps {
  book: BookFile;
}

export function BookCard({ book }: BookCardProps) {
  // Defensive checks
  if (!book || !book.filename) {
    return null;
  }

  const isProcessing = !["done", "failed"].includes(book.status);
  const isDone = book.status === "done";
  const isFailed = book.status === "failed";

  // Generate a gradient based on the book name for visual variety
  const gradientColors = [
    "from-violet-600 to-indigo-600",
    "from-emerald-600 to-teal-600",
    "from-amber-600 to-orange-600",
    "from-rose-600 to-pink-600",
    "from-cyan-600 to-blue-600",
    "from-purple-600 to-fuchsia-600",
  ];
  const gradientIndex = (book.filename?.length || 0) % gradientColors.length;
  const gradient = gradientColors[gradientIndex];

  const CardContent = (
    <motion.div
      className={`group relative bg-bg-secondary border border-border rounded-2xl overflow-hidden transition-all duration-300 ${
        isDone ? "hover:border-accent-primary/50 cursor-pointer" : ""
      }`}
      whileHover={isDone ? { y: -4, scale: 1.02 } : undefined}
    >
      {/* Cover Image / Gradient */}
      <div className={`relative h-44 bg-gradient-to-br ${gradient} overflow-hidden`}>
        {/* Pattern overlay */}
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
        
        {/* Book icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            className="w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-sm flex items-center justify-center"
            animate={isProcessing ? { scale: [1, 1.05, 1] } : {}}
            transition={{ duration: 2, repeat: isProcessing ? Infinity : 0 }}
          >
            <BookOpen className="w-8 h-8 text-white" />
          </motion.div>
        </div>

        {/* Status badge */}
        <div className="absolute top-3 right-3">
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            isDone 
              ? "bg-green-500/20 text-green-400 border border-green-500/30"
              : isFailed
              ? "bg-red-500/20 text-red-400 border border-red-500/30"
              : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
          }`}>
            {isDone && <CheckCircle className="w-3 h-3" />}
            {isFailed && <AlertCircle className="w-3 h-3" />}
            {isProcessing && <Loader2 className="w-3 h-3 animate-spin" />}
            <span>{getStatusLabel(book.status)}</span>
          </div>
        </div>

        {/* Hover overlay */}
        {isDone && (
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <span className="text-white font-medium">View Characters →</span>
          </div>
        )}
      </div>

      {/* Card content */}
      <div className="p-4">
        <h3 className="font-display font-semibold text-text-primary mb-1 truncate">
          {book.filename.replace(/\.pdf$/i, "")}
        </h3>
        
        <div className="flex items-center gap-4 text-sm text-text-muted">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>{formatRelativeTime(book.upload_date)}</span>
          </div>
          {book.character_count !== undefined && (
            <div className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" />
              <span>{book.character_count} characters</span>
            </div>
          )}
        </div>

        {/* Processing progress */}
        {isProcessing && (
          <div className="mt-3">
            <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary"
                initial={{ width: "10%" }}
                animate={{ width: book.status === "extracting_relationships" ? "80%" : book.status === "extracting_characters" ? "50%" : "30%" }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <p className="text-xs text-text-muted mt-2">
              {book.status === "queued" && "Waiting in queue..."}
              {book.status === "processing" && "Processing your book..."}
              {book.status === "extracting_characters" && "Discovering characters..."}
              {book.status === "extracting_relationships" && "Mapping relationships..."}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );

  if (isDone) {
    return (
      <Link href={`/book/${book.id}`}>
        {CardContent}
      </Link>
    );
  }

  return CardContent;
}

