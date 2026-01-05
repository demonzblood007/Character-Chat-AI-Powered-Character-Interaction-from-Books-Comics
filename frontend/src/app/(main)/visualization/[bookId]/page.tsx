"use client";

import { useEffect, useState, use } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, BookOpen, Sparkles } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { DashboardHeader } from "@/components/features/dashboard-header";
import { RelationshipGraph } from "@/components/features/relationship-graph";
import { api, Character, BookFile } from "@/lib/api";

interface PageProps {
  params: Promise<{ bookId: string }>;
}

// Demo data for when API is not available
const DEMO_CHARACTERS = [
  { id: "1", name: "Batman", description: "The Dark Knight of Gotham", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Batman" },
  { id: "2", name: "Joker", description: "The Clown Prince of Crime", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Joker" },
  { id: "3", name: "Robin", description: "Batman's trusted sidekick", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Robin" },
  { id: "4", name: "Alfred", description: "The loyal butler", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Alfred" },
  { id: "5", name: "Commissioner Gordon", description: "Gotham's police commissioner", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Gordon" },
  { id: "6", name: "Catwoman", description: "Master thief with complex motives", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Catwoman" },
  { id: "7", name: "Two-Face", description: "Former DA turned villain", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=TwoFace" },
  { id: "8", name: "Penguin", description: "Crime boss of Gotham", avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Penguin" },
];

const DEMO_RELATIONSHIPS = [
  { source: "1", target: "2", type: "rival" as const, description: "Arch-nemesis" },
  { source: "1", target: "3", type: "mentor" as const, description: "Mentor and ally" },
  { source: "1", target: "4", type: "family" as const, description: "Father figure" },
  { source: "1", target: "5", type: "friend" as const, description: "Ally in crime fighting" },
  { source: "1", target: "6", type: "romantic" as const, description: "Complex romantic tension" },
  { source: "2", target: "7", type: "rival" as const, description: "Competing villains" },
  { source: "2", target: "8", type: "rival" as const, description: "Criminal rivalry" },
  { source: "3", target: "4", type: "family" as const, description: "Alfred cares for Robin" },
  { source: "5", target: "7", type: "rival" as const, description: "Former friends, now enemies" },
  { source: "6", target: "8", type: "rival" as const, description: "Criminal competition" },
  { source: "7", target: "8", type: "friend" as const, description: "Criminal alliance" },
];

export default function VisualizationPage({ params }: PageProps) {
  const { bookId } = use(params);
  const [book, setBook] = useState<BookFile | null>(null);
  const [characters, setCharacters] = useState<typeof DEMO_CHARACTERS>([]);
  const [relationships, setRelationships] = useState<typeof DEMO_RELATIONSHIPS>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        // Try to fetch real data
        const bookData = await api.getFileStatus(bookId);
        setBook(bookData);
        
        if (bookData.status === "done") {
          const chars = await api.getCharacters(bookId);
          // Transform API characters to graph format
          const graphChars = chars.map((c: Character, i: number) => ({
            id: String(i + 1),
            name: c.name,
            description: c.description,
            avatar: c.avatar,
          }));
          setCharacters(graphChars);
          
          // Extract relationships from characters
          const rels: typeof DEMO_RELATIONSHIPS = [];
          chars.forEach((char: Character, charIndex: number) => {
            char.relationships?.forEach((rel: { target: string; type: string }) => {
              const targetIndex = chars.findIndex((c: Character) => c.name === rel.target);
              if (targetIndex !== -1) {
                rels.push({
                  source: String(charIndex + 1),
                  target: String(targetIndex + 1),
                  type: (rel.type as any) || "friend",
                  description: `${rel.type || "friend"} relationship`,
                });
              }
            });
          });
          setRelationships(rels);
        }
      } catch (error) {
        console.debug("Using demo data for visualization");
        // Use demo data
        setBook({
          id: bookId,
          filename: "The Dark Knight Returns.pdf",
          upload_date: new Date().toISOString(),
          status: "done",
          character_count: DEMO_CHARACTERS.length,
          relationship_count: DEMO_RELATIONSHIPS.length,
        });
        setCharacters(DEMO_CHARACTERS);
        setRelationships(DEMO_RELATIONSHIPS);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [bookId]);

  const handleCharacterClick = (character: { id: string; name: string; avatar?: string; description?: string }) => {
    console.log("Character clicked:", character);
  };

  return (
    <div className="min-h-screen bg-bg-primary">
      <DashboardHeader />

      {/* Hero Section */}
      <section className="relative py-8 overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          <Image
            src="https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1920&q=80"
            alt="Library"
            fill
            className="object-cover opacity-10"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-bg-primary via-bg-primary/95 to-bg-primary" />
        </div>

        <div className="container-app relative z-10">
          {/* Back button */}
          <Link href={`/book/${bookId}`}>
            <button className="btn-ghost mb-6 flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back to Book
            </button>
          </Link>

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <div className="flex items-center gap-3 mb-2">
              <Sparkles className="w-5 h-5 text-accent-secondary" />
              <span className="text-accent-secondary text-sm font-medium uppercase tracking-[0.2em]">
                Relationship Map
              </span>
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-light">
              Character <span className="text-gradient italic font-medium">Connections</span>
            </h1>
            <p className="text-text-secondary mt-3 max-w-2xl">
              Explore the intricate web of relationships between characters. 
              Click on any character to learn more and start a conversation.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Graph Section */}
      <main className="container-app pb-16">
        {isLoading ? (
          <div className="h-[600px] rounded-2xl border border-border bg-bg-secondary flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center"
            >
              <div className="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-accent-primary border-t-transparent animate-spin" />
              <p className="text-text-secondary">Loading relationship map...</p>
            </motion.div>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <RelationshipGraph
              characters={characters}
              relationships={relationships}
              bookTitle={book?.filename.replace(/\.pdf$/i, "") || "Book"}
              onCharacterClick={handleCharacterClick}
            />
          </motion.div>
        )}

        {/* Stats */}
        {!isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            <div className="bento-card p-5 text-center">
              <p className="text-3xl font-display font-semibold text-gradient mb-1">
                {characters.length}
              </p>
              <p className="text-sm text-text-muted">Characters</p>
            </div>
            <div className="bento-card p-5 text-center">
              <p className="text-3xl font-display font-semibold text-gradient mb-1">
                {relationships.length}
              </p>
              <p className="text-sm text-text-muted">Connections</p>
            </div>
            <div className="bento-card p-5 text-center">
              <p className="text-3xl font-display font-semibold text-gradient mb-1">
                {relationships.filter(r => r.type === "romantic").length}
              </p>
              <p className="text-sm text-text-muted">Romantic</p>
            </div>
            <div className="bento-card p-5 text-center">
              <p className="text-3xl font-display font-semibold text-gradient mb-1">
                {relationships.filter(r => r.type === "rival").length}
              </p>
              <p className="text-sm text-text-muted">Rivalries</p>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}

