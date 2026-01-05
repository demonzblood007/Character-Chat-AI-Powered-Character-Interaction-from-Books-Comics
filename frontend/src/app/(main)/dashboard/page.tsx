"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { 
  Plus, 
  BookOpen, 
  MessageSquare, 
  Users, 
  Sparkles, 
  TrendingUp, 
  Clock,
  ArrowRight,
  Upload,
  Library,
  Star
} from "lucide-react";
import { Button, Card, SkeletonCard } from "@/components/ui";
import { useAuthStore } from "@/stores/auth-store";
import { useBooksStore } from "@/stores/books-store";
import { BookCard } from "@/components/features/book-card";
import { UploadModal } from "@/components/features/upload-modal";
import { WelcomeModal } from "@/components/features/welcome-modal";
import { DashboardHeader } from "@/components/features/dashboard-header";
import RecentCharacters from "@/components/features/recent-characters";

// Beautiful background images
const HERO_IMAGES = [
  "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1920&q=80",
  "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1920&q=80",
  "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=1920&q=80",
];

export default function DashboardPage() {
  const { user, checkAuth } = useAuthStore();
  const { books, isLoading, error, fetchBooks } = useBooksStore();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Ensure auth check completes before fetching books
    const initializeDashboard = async () => {
      try {
        await checkAuth();
        console.log("✅ Auth check complete, now fetching books...");
        await fetchBooks();
      } catch (error) {
        console.error("❌ Dashboard initialization failed:", error);
      }
    };

    initializeDashboard();

    const hasSeenWelcome = localStorage.getItem("hasSeenWelcome");
    if (!hasSeenWelcome) {
      setShowWelcome(true);
    }
  }, [checkAuth, fetchBooks]);

  // Poll for book status updates if there are processing books
  useEffect(() => {
    const processingBooks = books.filter(
      (book) => !["done", "failed"].includes(book.status)
    );
    
    if (processingBooks.length === 0) return;

    const pollInterval = setInterval(() => {
      fetchBooks(); // Refresh books to get updated status
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(pollInterval);
  }, [books, fetchBooks]);

  const handleWelcomeClose = () => {
    localStorage.setItem("hasSeenWelcome", "true");
    setShowWelcome(false);
  };

  const stats = [
    {
      icon: BookOpen,
      label: "Books",
      value: user?.stats.books_uploaded || 0,
      gradient: "from-violet-500 to-purple-600",
    },
    {
      icon: Users,
      label: "Characters",
      value: user?.stats.characters_created || 0,
      gradient: "from-emerald-500 to-teal-600",
    },
    {
      icon: MessageSquare,
      label: "Chats",
      value: user?.stats.total_chats || 0,
      gradient: "from-amber-500 to-orange-600",
    },
    {
      icon: Sparkles,
      label: "Credits",
      value: user?.subscription.credits || 0,
      gradient: "from-rose-500 to-pink-600",
    },
  ];

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-bg-primary">
      <DashboardHeader />
      
      {/* Hero Section with Stats */}
      <section className="relative py-12 overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          <Image
            src={HERO_IMAGES[0]}
            alt="Library"
            fill
            className="object-cover opacity-10"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-bg-primary via-bg-primary/95 to-bg-primary" />
        </div>

        <div className="container-app relative z-10">
          {/* Welcome Message */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-10"
          >
            <span className="text-accent-secondary text-sm font-medium uppercase tracking-[0.2em]">
              Welcome back
            </span>
            <h1 className="font-display text-4xl md:text-5xl font-light mt-2">
              {user?.name ? (
                <>
                  Hello, <span className="text-gradient italic font-medium">{user.name.split(' ')[0]}</span>
                </>
              ) : (
                <>
                  Your <span className="text-gradient italic font-medium">Library</span>
                </>
              )}
            </h1>
          </motion.div>

          {/* Bento Grid Stats Layout */}
          <div className="grid grid-cols-1 md:grid-cols-6 lg:grid-cols-12 gap-4 md:gap-6">
            {/* Large welcome/overview card */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
              className="md:col-span-6 lg:col-span-8"
            >
              <div className="bento-card p-6 md:p-8 h-full relative overflow-hidden">
                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-accent-primary to-accent-violet flex items-center justify-center">
                      <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-display text-xl md:text-2xl font-medium text-text-primary">
                        Welcome back, {user?.name?.split(' ')[0] || 'Creator'}
                      </h3>
                      <p className="text-text-secondary text-sm">
                        Ready to continue your literary adventures?
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                    {stats.slice(0, 4).map((stat, index) => (
                      <div key={stat.label} className="text-center">
                        <div className={`w-10 h-10 mx-auto mb-2 rounded-lg bg-gradient-to-br ${stat.gradient} flex items-center justify-center`}>
                          <stat.icon className="w-5 h-5 text-white" />
                        </div>
                        <p className="text-lg font-display font-semibold text-text-primary">
                          {stat.value.toLocaleString()}
                        </p>
                        <p className="text-xs text-text-muted uppercase tracking-wider">
                          {stat.label}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
                {/* Background decoration */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-accent-primary/10 to-accent-violet/10 rounded-full blur-3xl" />
              </div>
            </motion.div>

            {/* Quick Actions Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="md:col-span-3 lg:col-span-4"
            >
              <div className="bento-card p-6 h-full">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-secondary to-accent-orange flex items-center justify-center">
                    <Plus className="w-4 h-4 text-white" />
                  </div>
                  <h3 className="font-display text-lg font-medium text-text-primary">
                    Quick Actions
                  </h3>
                </div>
                <div className="space-y-3">
                  <button
                    onClick={() => setIsUploadOpen(true)}
                    className="w-full btn-ghost text-sm flex items-center justify-center gap-2 hover:border-accent-primary hover:text-accent-primary transition-all"
                  >
                    <Upload className="w-4 h-4" />
                    Upload New Book
                  </button>
                  <button className="w-full btn-ghost text-sm flex items-center justify-center gap-2 hover:border-accent-cyan hover:text-accent-cyan transition-all">
                    <MessageSquare className="w-4 h-4" />
                    Start Chat
                  </button>
                  <button className="w-full btn-ghost text-sm flex items-center justify-center gap-2 hover:border-accent-emerald hover:text-accent-emerald transition-all">
                    <Users className="w-4 h-4" />
                    Explore Characters
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <main className="container-app pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8">
          {/* Main content - Book Library */}
          <div className="lg:col-span-8">
            {/* Section Header */}
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center">
                  <Library className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="font-display text-2xl font-medium text-text-primary">
                    Your Collection
                  </h2>
                  <p className="text-text-muted text-sm">
                    {books.length === 0
                      ? "Start your journey"
                      : `${books.length} book${books.length !== 1 ? "s" : ""}`}
                  </p>
                </div>
              </div>
              <Button
                onClick={() => setIsUploadOpen(true)}
                leftIcon={<Plus className="w-5 h-5" />}
                className="btn-magic"
              >
                Upload Book
              </Button>
            </div>

            {/* Error State */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-3xl border border-red-500/50 bg-red-500/10 p-8"
              >
                <div className="text-center">
                  <h3 className="font-display text-xl font-medium text-red-400 mb-2">
                    Error Loading Books
                  </h3>
                  <p className="text-text-secondary mb-4">{error}</p>
                  <Button
                    onClick={() => fetchBooks()}
                    leftIcon={<Upload className="w-4 h-4" />}
                    className="btn-magic"
                  >
                    Retry
                  </Button>
                </div>
              </motion.div>
            )}

            {/* Empty State - Beautiful Design */}
            {!isLoading && !error && books.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-3xl border border-border"
              >
                {/* Background Image */}
                <div className="absolute inset-0">
                  <Image
                    src="https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=1200&q=80"
                    alt="Magic books"
                    fill
                    className="object-cover opacity-20"
                  />
                  <div className="absolute inset-0 bg-gradient-to-r from-bg-secondary via-bg-secondary/90 to-transparent" />
                </div>

                <div className="relative z-10 p-12 md:p-16 max-w-xl">
                  <motion.div
                    animate={{ y: [0, -8, 0] }}
                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                    className="w-20 h-20 mb-8 rounded-2xl bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center shadow-lg shadow-accent-primary/30"
                  >
                    <Upload className="w-10 h-10 text-white" />
                  </motion.div>
                  
                  <h3 className="font-display text-3xl font-light text-text-primary mb-4">
                    Begin Your <span className="text-gradient italic font-medium">Adventure</span>
                  </h3>
                  <p className="text-text-secondary text-lg mb-8 leading-relaxed">
                    Upload your first book and watch as AI brings every character to life. 
                    Sherlock, Elizabeth Bennet, Gatsby — they're all waiting.
                  </p>
                  
                  <button
                    onClick={() => setIsUploadOpen(true)}
                    className="btn-magic flex items-center gap-3 group"
                  >
                    <BookOpen className="w-5 h-5" />
                    <span>Upload Your First Book</span>
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                  </button>
                </div>
              </motion.div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="bento-card p-4 h-80">
                    <div className="skeleton h-48 rounded-xl mb-4" />
                    <div className="skeleton h-6 w-3/4 mb-2" />
                    <div className="skeleton h-4 w-1/2" />
                  </div>
                ))}
              </div>
            )}

            {/* Book Grid - Cinematic Style */}
            {!isLoading && books.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6"
              >
                <AnimatePresence>
                  {books
                    .filter((book) => book && book.filename)
                    .map((book, index) => (
                    <motion.div
                      key={book.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <BookCard book={book} />
                    </motion.div>
                  ))}
                </AnimatePresence>
              </motion.div>
            )}
          </div>

          {/* Sidebar - Bento Grid */}
          <div className="lg:col-span-4 grid grid-cols-1 gap-6">
            {/* Subscription & Usage Card - Large */}
            <div className="bento-card p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-accent-primary/20 to-transparent rounded-full blur-2xl" />
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-display text-xl font-medium text-text-primary">
                    Your Plan
                  </h3>
                  <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                    user?.subscription.tier === "premium"
                      ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white"
                      : user?.subscription.tier === "pro"
                      ? "bg-gradient-to-r from-accent-primary to-accent-violet text-white"
                      : "bg-bg-tertiary text-text-secondary"
                  }`}>
                    {user?.subscription.tier?.toUpperCase() || "FREE"}
                  </span>
                </div>
                <div className="space-y-3 mb-6">
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary text-sm">Credits</span>
                    <span className="text-text-primary font-semibold">{user?.subscription.credits || 0}</span>
                  </div>
                  <div className="w-full bg-bg-tertiary rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-accent-primary to-accent-violet h-2 rounded-full transition-all"
                      style={{ width: `${Math.min((user?.subscription.credits || 0) / 100 * 100, 100)}%` }}
                    />
                  </div>
                </div>
                {user?.subscription.tier === "free" && (
                  <button className="btn-magic w-full text-sm flex items-center justify-center gap-2">
                    <Star className="w-4 h-4" />
                    Upgrade to Pro
                  </button>
                )}
              </div>
            </div>

            {/* Recent Activity Card */}
            <div className="bento-card p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-secondary to-accent-orange flex items-center justify-center">
                  <Clock className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-medium text-text-primary">
                    Recent Activity
                  </h3>
                  <p className="text-text-secondary text-sm">Your latest conversations</p>
                </div>
              </div>
              <RecentCharacters />
            </div>
          </div>
        </div>
      </main>

      {/* Upload Modal */}
      <UploadModal 
        isOpen={isUploadOpen} 
        onClose={() => setIsUploadOpen(false)} 
      />

      {/* Welcome Modal */}
      <WelcomeModal
        isOpen={showWelcome}
        onClose={handleWelcomeClose}
      />
    </div>
  );
}
