"use client";

import { useEffect, useState, use } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  MessageSquare,
  Sparkles,
  BookOpen,
  Users,
  Heart,
  Swords,
  User,
} from "lucide-react";
import Link from "next/link";
import { Button, Avatar, Card } from "@/components/ui";
import { DashboardHeader } from "@/components/features/dashboard-header";
import { api, Character } from "@/lib/api";
import { getRelationshipColor } from "@/lib/utils";

interface PageProps {
  params: Promise<{ name: string }>;
}

export default function CharacterProfilePage({ params }: PageProps) {
  const { name: characterName } = use(params);
  const decodedName = decodeURIComponent(characterName);
  
  const [character, setCharacter] = useState<Character | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCharacter = async () => {
      try {
        const char = await api.getCharacter(decodedName);
        setCharacter(char);
      } catch (error) {
        console.error("Failed to load character:", error);
        // Demo data for preview
        setCharacter({
          name: decodedName,
          description:
            "A complex and compelling character whose journey through the story reveals themes of courage, sacrifice, and growth. Their decisions shape the narrative in profound ways.",
          powers: ["Determination", "Intelligence", "Leadership", "Empathy"],
          story_arcs: ["The Beginning", "The Challenge", "The Transformation", "The Resolution"],
          avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(decodedName)}`,
          relationships: [
            { target: "Ally One", type: "ally" },
            { target: "Enemy One", type: "enemy" },
            { target: "Family Member", type: "family" },
            { target: "Friend", type: "friend" },
          ],
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadCharacter();
  }, [decodedName]);

  const getRelationshipIcon = (type: string) => {
    switch (type) {
      case "ally":
      case "friend":
        return Users;
      case "enemy":
        return Swords;
      case "family":
        return Heart;
      default:
        return User;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <DashboardHeader />

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0 bg-gradient-to-b from-accent-primary/20 via-bg-primary to-bg-primary" />
        <motion.div
          className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-accent-primary/10 blur-[100px]"
          animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 8, repeat: Infinity }}
        />

        <div className="container-app relative z-10 py-12">
          {/* Back button */}
          <Link href="/dashboard" className="inline-block mb-8">
            <Button variant="ghost" leftIcon={<ArrowLeft className="w-5 h-5" />}>
              Back to Library
            </Button>
          </Link>

          {/* Character hero */}
          <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12">
            {/* Avatar */}
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
            >
              <Avatar
                src={character?.avatar}
                name={character?.name || decodedName}
                size="2xl"
                showRing
                ringColor="primary"
                className="shadow-2xl shadow-accent-primary/20"
              />
            </motion.div>

            {/* Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-center md:text-left"
            >
              <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
                <Sparkles className="w-5 h-5 text-accent-primary" />
                <span className="text-sm text-accent-primary font-medium">Character Profile</span>
              </div>
              
              <h1 className="font-display text-4xl md:text-5xl font-bold text-text-primary mb-4">
                {character?.name || decodedName}
              </h1>
              
              <p className="text-lg text-text-secondary max-w-xl mb-6">
                {character?.description}
              </p>

              <Link href={`/chat/${encodeURIComponent(decodedName)}`}>
                <Button size="lg" leftIcon={<MessageSquare className="w-5 h-5" />}>
                  Start Conversation
                </Button>
              </Link>
            </motion.div>
          </div>
        </div>
      </div>

      <main className="container-app py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Powers / Traits */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card hover={false} className="p-6 h-full">
              <h2 className="font-display text-xl font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-accent-primary" />
                Powers & Traits
              </h2>
              <div className="space-y-3">
                {character?.powers.map((power, index) => (
                  <motion.div
                    key={power}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + index * 0.1 }}
                    className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary"
                  >
                    <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
                      <span className="text-accent-primary font-bold text-sm">
                        {index + 1}
                      </span>
                    </div>
                    <span className="text-text-primary font-medium">{power}</span>
                  </motion.div>
                ))}
              </div>
            </Card>
          </motion.div>

          {/* Story Arcs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card hover={false} className="p-6 h-full">
              <h2 className="font-display text-xl font-semibold text-text-primary mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-accent-secondary" />
                Story Arcs
              </h2>
              <div className="space-y-3">
                {character?.story_arcs.map((arc, index) => (
                  <motion.div
                    key={arc}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary"
                  >
                    <div className="w-8 h-8 rounded-lg bg-accent-secondary/10 flex items-center justify-center">
                      <BookOpen className="w-4 h-4 text-accent-secondary" />
                    </div>
                    <span className="text-text-primary font-medium">{arc}</span>
                  </motion.div>
                ))}
              </div>
            </Card>
          </motion.div>

          {/* Relationships */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card hover={false} className="p-6 h-full">
              <h2 className="font-display text-xl font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-emerald-400" />
                Relationships
              </h2>
              <div className="space-y-3">
                {character?.relationships.map((rel, index) => {
                  const Icon = getRelationshipIcon(rel.type);
                  const color = getRelationshipColor(rel.type);
                  
                  return (
                    <motion.div
                      key={rel.target}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.6 + index * 0.1 }}
                    >
                      <Link
                        href={`/character/${encodeURIComponent(rel.target)}`}
                        className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary hover:bg-bg-elevated transition-colors group"
                      >
                        <Avatar
                          src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(rel.target)}`}
                          name={rel.target}
                          size="sm"
                        />
                        <div className="flex-1">
                          <p className="text-text-primary font-medium group-hover:text-accent-primary transition-colors">
                            {rel.target}
                          </p>
                          <p className="text-xs capitalize" style={{ color }}>
                            {rel.type}
                          </p>
                        </div>
                        <Icon className="w-4 h-4" style={{ color }} />
                      </Link>
                    </motion.div>
                  );
                })}
              </div>
            </Card>
          </motion.div>
        </div>

        {/* Chat Preview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="mt-12"
        >
          <Card hover={false} className="p-8 text-center">
            <Avatar
              src={character?.avatar}
              name={character?.name || decodedName}
              size="xl"
              className="mx-auto mb-6"
            />
            <h3 className="font-display text-2xl font-bold text-text-primary mb-2">
              Ready to Chat?
            </h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              Start a conversation with {character?.name || decodedName} and explore their 
              thoughts, feelings, and story in depth.
            </p>
            <Link href={`/chat/${encodeURIComponent(decodedName)}`}>
              <Button size="lg" leftIcon={<MessageSquare className="w-5 h-5" />}>
                Start Chatting Now
              </Button>
            </Link>
          </Card>
        </motion.div>
      </main>
    </div>
  );
}

