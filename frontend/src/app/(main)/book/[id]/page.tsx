"use client";

import { useEffect, useState, use } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  BookOpen,
  Users,
  Network,
  MessageSquare,
  Clock,
  CheckCircle,
} from "lucide-react";
import Link from "next/link";
import { Button, Avatar, Card, Skeleton } from "@/components/ui";
import { DashboardHeader } from "@/components/features/dashboard-header";
import { useBooksStore } from "@/stores/books-store";
import { api, Character, BookFile } from "@/lib/api";
import { formatRelativeTime, getStatusLabel } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function BookDetailPage({ params }: PageProps) {
  const { id: bookId } = use(params);
  const { fetchBookStatus, pollBookStatus } = useBooksStore();
  
  const [book, setBook] = useState<BookFile | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadBookData = async () => {
      try {
        // Fetch book status
        const bookData = await fetchBookStatus(bookId);
        setBook(bookData);

        // If book is done, fetch characters
        if (bookData.status === "done") {
          const chars = await api.getCharacters(bookId);
          setCharacters(chars);
        }
      } catch (error) {
        console.error("Failed to load book:", error);
        // Demo data for preview
        setBook({
          id: bookId,
          filename: "The Dark Knight Returns.pdf",
          upload_date: new Date().toISOString(),
          status: "done",
          character_count: 8,
          relationship_count: 15,
        });
        setCharacters([
          {
            name: "Batman",
            description: "The Dark Knight, a vigilante who fights crime in Gotham City.",
            powers: ["Martial Arts", "Detective Skills", "Technology"],
            story_arcs: ["Year One", "The Long Halloween"],
            avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Batman",
            relationships: [
              { target: "Joker", type: "enemy" },
              { target: "Robin", type: "ally" },
            ],
          },
          {
            name: "Joker",
            description: "The Clown Prince of Crime, Batman's greatest nemesis.",
            powers: ["Genius Intellect", "Chemical Expertise", "Unpredictability"],
            story_arcs: ["The Killing Joke", "Death of the Family"],
            avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Joker",
            relationships: [{ target: "Batman", type: "enemy" }],
          },
          {
            name: "Robin",
            description: "Batman's trusted sidekick and protégé.",
            powers: ["Acrobatics", "Martial Arts", "Technology"],
            story_arcs: ["A Death in the Family", "Under the Red Hood"],
            avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Robin",
            relationships: [{ target: "Batman", type: "ally" }],
          },
          {
            name: "Alfred",
            description: "The loyal butler and father figure to Bruce Wayne.",
            powers: ["Medical Knowledge", "Combat Training", "Wisdom"],
            story_arcs: ["Year One", "The Dark Knight Returns"],
            avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Alfred",
            relationships: [{ target: "Batman", type: "family" }],
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    loadBookData();

    // Poll for status if still processing
    const stopPolling = pollBookStatus(bookId);
    return () => stopPolling();
  }, [bookId, fetchBookStatus, pollBookStatus]);

  const isProcessing = book && !["done", "failed"].includes(book.status);

  // Generate gradient based on book name
  const gradientColors = [
    "from-violet-600 to-indigo-600",
    "from-emerald-600 to-teal-600",
    "from-amber-600 to-orange-600",
    "from-rose-600 to-pink-600",
  ];
  const gradientIndex = (book?.filename.length || 0) % gradientColors.length;
  const gradient = gradientColors[gradientIndex];

  return (
    <div className="min-h-screen bg-bg-primary">
      <DashboardHeader />

      {/* Hero Section */}
      <div className={`relative h-64 bg-gradient-to-br ${gradient} overflow-hidden`}>
        {/* Pattern overlay */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        {/* Back button */}
        <div className="absolute top-6 left-6">
          <Link href="/dashboard">
            <Button variant="ghost" className="bg-black/20 hover:bg-black/40 text-white border-0">
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back to Library
            </Button>
          </Link>
        </div>

        {/* Book icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 15 }}
            className="w-24 h-24 rounded-2xl bg-white/10 backdrop-blur-sm flex items-center justify-center"
          >
            <BookOpen className="w-12 h-12 text-white" />
          </motion.div>
        </div>
      </div>

      <main className="container-app py-8 -mt-16 relative z-10">
        {/* Book Info Card */}
        <Card hover={false} className="mb-8 p-6">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="flex-1">
              <h1 className="font-display text-3xl font-bold text-text-primary mb-2">
                {isLoading ? (
                  <Skeleton className="h-10 w-64" />
                ) : (
                  book?.filename.replace(/\.pdf$/i, "") || "Unknown Book"
                )}
              </h1>

              <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
                {isLoading ? (
                  <Skeleton className="h-5 w-32" />
                ) : (
                  <>
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      Uploaded {formatRelativeTime(book?.upload_date || "")}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Users className="w-4 h-4" />
                      {book?.character_count || 0} characters
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Network className="w-4 h-4" />
                      {book?.relationship_count || 0} relationships
                    </span>
                    <span
                      className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                        book?.status === "done"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-amber-500/20 text-amber-400"
                      }`}
                    >
                      {book?.status === "done" && <CheckCircle className="w-3 h-3" />}
                      {getStatusLabel(book?.status || "")}
                    </span>
                  </>
                )}
              </div>
            </div>

            {book?.status === "done" && (
              <Link href={`/visualization/${bookId}`}>
                <Button variant="secondary" leftIcon={<Network className="w-5 h-5" />}>
                  View Relationships
                </Button>
              </Link>
            )}
          </div>

          {/* Processing progress */}
          {isProcessing && (
            <div className="mt-6 p-4 bg-bg-tertiary rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <BookOpen className="w-4 h-4 text-amber-400" />
                  </motion.div>
                </div>
                <div>
                  <p className="font-medium text-text-primary">
                    {getStatusLabel(book.status)}
                  </p>
                  <p className="text-sm text-text-muted">
                    This usually takes 1-3 minutes
                  </p>
                </div>
              </div>
              <div className="h-2 bg-bg-secondary rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-amber-500 to-orange-500"
                  initial={{ width: "10%" }}
                  animate={{
                    width:
                      book.status === "extracting_relationships"
                        ? "80%"
                        : book.status === "extracting_characters"
                        ? "50%"
                        : "30%",
                  }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          )}
        </Card>

        {/* Characters Section */}
        {book?.status === "done" && (
          <>
            <h2 className="font-display text-2xl font-bold text-text-primary mb-6 flex items-center gap-3">
              <Users className="w-6 h-6 text-accent-primary" />
              Characters ({characters.length})
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {isLoading
                ? [...Array(4)].map((_, i) => (
                    <Card key={i} hover={false} className="p-6">
                      <div className="flex flex-col items-center text-center">
                        <Skeleton className="w-20 h-20 rounded-full mb-4" variant="circular" />
                        <Skeleton className="h-6 w-24 mb-2" />
                        <Skeleton className="h-4 w-full mb-4" />
                        <Skeleton className="h-10 w-full" />
                      </div>
                    </Card>
                  ))
                : characters.map((character, index) => (
                    <motion.div
                      key={character.name}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <Card className="p-6 h-full" glow>
                        <div className="flex flex-col items-center text-center h-full">
                          <Avatar
                            src={character.avatar}
                            name={character.name}
                            size="xl"
                            showRing
                            ringColor="primary"
                            className="mb-4"
                          />
                          <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
                            {character.name}
                          </h3>
                          <p className="text-sm text-text-secondary mb-4 line-clamp-2 flex-1">
                            {character.description}
                          </p>

                          {/* Powers tags */}
                          <div className="flex flex-wrap justify-center gap-1 mb-4">
                            {character.powers.slice(0, 3).map((power) => (
                              <span
                                key={power}
                                className="px-2 py-0.5 bg-accent-primary/10 text-accent-primary rounded-full text-xs"
                              >
                                {power}
                              </span>
                            ))}
                          </div>

                          <Link
                            href={`/chat/${encodeURIComponent(character.name)}`}
                            className="w-full mt-auto"
                          >
                            <Button className="w-full" leftIcon={<MessageSquare className="w-4 h-4" />}>
                              Chat Now
                            </Button>
                          </Link>
                        </div>
                      </Card>
                    </motion.div>
                  ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

