"use client";

import { useEffect, useState } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { 
  ArrowRight, 
  Play, 
  BookOpen, 
  Sparkles, 
  Heart,
  MessageCircle,
  Users,
  Zap,
  Shield,
  Star,
  ChevronDown,
  Menu,
  X
} from "lucide-react";
import { Logo, LogoMark } from "@/components/ui/logo";

// High-quality Unsplash images for immersive experience
const IMAGES = {
  heroLibrary: "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1920&q=95",
  bookShelf: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1200&q=85",
  openBook: "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&q=85",
  oldLibrary: "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=1200&q=85",
  readingPerson: "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=800&q=85",
  bookStack: "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=600&q=85",
  magicBooks: "https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=1200&q=85",
  cozyReading: "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&q=85",
};

// Featured characters for showcase (women-forward + includes comics)
// Using high-quality character-appropriate avatars
const FEATURED_CHARACTERS = [
  {
    name: "Wonder Woman",
    book: "DC Comics",
    quote: "I will fight for those who cannot fight for themselves.",
    image: `https://api.dicebear.com/7.x/adventurer/svg?seed=wonderwoman&backgroundColor=b6e3f4&clothingColor=262e33&skinColor=fdbcb4&hairColor=4a312c&size=400`,
  },
  {
    name: "Spider-Gwen",
    book: "Marvel Comics",
    quote: "Sometimes you have to be brave enough to be different.",
    image: `https://api.dicebear.com/7.x/adventurer/svg?seed=spidergwen&backgroundColor=c7d2fe&clothingColor=1f2937&skinColor=fdbcb4&hairColor=2c1b19&size=400`,
  },
  {
    name: "Hermione Granger",
    book: "Harry Potter",
    quote: "Books! And cleverness! There are more important things — friendship and bravery.",
    image: `https://api.dicebear.com/7.x/adventurer/svg?seed=hermione&backgroundColor=ffd5dc&clothingColor=262e33&skinColor=fdbcb4&hairColor=6b4423&size=400`,
  },
  {
    name: "Elizabeth Bennet",
    book: "Pride and Prejudice",
    quote: "I could easily forgive his pride, if he had not mortified mine.",
    image: `https://api.dicebear.com/7.x/adventurer/svg?seed=elizabethbennet&backgroundColor=fce7f3&clothingColor=1f2937&skinColor=fdbcb4&hairColor=8b4513&size=400`,
  },
  {
    name: "Katniss Everdeen",
    book: "The Hunger Games",
    quote: "I am more than just a piece in their Games.",
    image: `https://api.dicebear.com/7.x/adventurer/svg?seed=katniss&backgroundColor=d1d5db&clothingColor=1f2937&skinColor=fdbcb4&hairColor=2c1b19&size=400`,
  },
  {
    name: "Sherlock Holmes",
    book: "A Study in Scarlet",
    quote: "When you have eliminated the impossible, whatever remains must be the truth.",
    image: `https://api.dicebear.com/7.x/adventurer/svg?seed=sherlock&backgroundColor=ddd6fe&clothingColor=1f2937&skinColor=edb98a&hairColor=4a312c&size=400`,
  },
];

// Testimonials (women-forward + more diverse)
const TESTIMONIALS = [
  {
    text: "I chatted with Wonder Woman about courage and leadership. It felt like therapy — but cinematic.",
    author: "Priya S.",
    role: "Literature Professor",
    avatar: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&q=95",
  },
  {
    text: "The relationship map made my comic universe feel *alive*. I could literally see tensions and alliances.",
    author: "Aisha K.",
    role: "Book Club Host",
    avatar: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=200&h=200&fit=crop&q=95",
  },
  {
    text: "My students are excited again — they’re talking to characters instead of just writing essays about them.",
    author: "Dr. Maya Chen",
    role: "High School Teacher",
    avatar: "https://images.unsplash.com/photo-1607746882042-944635dfe10e?w=200&h=200&fit=crop&q=95",
  },
];

export default function Home() {
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.2], [1, 1.1]);
  const [mounted, setMounted] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  if (!mounted) return null;

  return (
    <main className="relative bg-bg-primary overflow-hidden">
      {/* ========== STICKY NAVBAR ========== */}
      <motion.nav
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled ? 'glass-strong py-3' : 'py-5 bg-transparent'
        }`}
      >
        <div className="container-app flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <div className="heartbeat">
              <Logo size="md" animated={false} className="hidden sm:flex" />
            </div>
            <LogoMark size={40} className="sm:hidden" />
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
              Features
            </a>
            <a href="#demo" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
              Demo
            </a>
            <a href="#testimonials" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
              Stories
            </a>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-4">
            <Link href="/login" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
              Sign In
            </Link>
            <Link href="/login">
              <button className="btn-magic text-sm py-2.5 px-5">
                Get Started
              </button>
            </Link>
          </div>

          {/* Mobile Menu Toggle */}
          <button
            className="md:hidden w-10 h-10 flex items-center justify-center text-text-primary"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden glass-strong border-t border-border mt-3"
            >
              <div className="container-app py-6 flex flex-col gap-4">
                <a href="#features" className="text-text-secondary hover:text-text-primary transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Features
                </a>
                <a href="#demo" className="text-text-secondary hover:text-text-primary transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Demo
                </a>
                <a href="#testimonials" className="text-text-secondary hover:text-text-primary transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Stories
                </a>
                <hr className="border-border" />
                <Link href="/login" className="text-text-secondary hover:text-text-primary transition-colors">
                  Sign In
                </Link>
                <Link href="/login">
                  <button className="btn-magic w-full">
                    Get Started
                  </button>
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.nav>
      {/* ========== HERO SECTION ========== */}
      <section className="relative min-h-[100vh] flex items-center justify-center">
        {/* Background Image with Parallax */}
        <motion.div 
          className="absolute inset-0"
          style={{ scale: heroScale }}
        >
        <Image
            src={IMAGES.heroLibrary}
            alt="Ancient library"
            fill
            className="object-cover"
          priority
            quality={95}
          />
          {/* Gradient overlays for depth */}
          <div className="absolute inset-0 bg-gradient-to-b from-bg-primary/40 via-bg-primary/60 to-bg-primary" />
          <div className="absolute inset-0 bg-gradient-to-r from-bg-primary/80 via-transparent to-bg-primary/80" />
          {/* Vignette */}
          <div className="absolute inset-0" style={{ boxShadow: 'inset 0 0 200px 80px rgba(5,5,8,0.9)' }} />
        </motion.div>

        {/* Floating particles */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {[...Array(20)].map((_, i) => (
            <motion.div
              key={i}
              className={`absolute w-1 h-1 rounded-full ${
                i % 3 === 0 ? 'bg-accent-primary/40' :
                i % 3 === 1 ? 'bg-accent-secondary/40' : 'bg-accent-emerald/40'
              }`}
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
              }}
              animate={{
                y: [-20, -100],
                x: [0, Math.random() * 20 - 10],
                opacity: [0, 1, 0],
                scale: [1, 1.5, 1],
              }}
              transition={{
                duration: 3 + Math.random() * 4,
                repeat: Infinity,
                delay: Math.random() * 5,
              }}
            />
          ))}
        </div>

        {/* Content */}
        <motion.div 
          className="relative z-10 container-app text-center px-4"
          style={{ opacity: heroOpacity }}
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full glass-glow mb-8"
          >
            <Heart className="w-4 h-4 text-rose-400" />
            <span className="text-sm font-medium text-text-secondary">
              Created by <span className="text-accent-primary">Bhavik</span>
            </span>
          </motion.div>

          {/* Main Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="font-display text-5xl md:text-7xl lg:text-8xl font-light mb-6 tracking-tight"
          >
            <span className="block text-text-primary">Step Into Your</span>
            <span className="block mt-2 text-gradient font-medium italic">
              Favorite Stories
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="max-w-2xl mx-auto text-lg md:text-xl text-text-secondary mb-10 font-light leading-relaxed"
          >
            Upload any book. Meet every character. Have conversations that feel 
            <span className="text-accent-secondary font-medium"> impossibly real</span>.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <Link href="/login">
              <button className="btn-magic flex items-center gap-3 group">
                <BookOpen className="w-5 h-5" />
                <span>Begin Your Journey</span>
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>
            </Link>
            <button 
              className="btn-ghost flex items-center gap-3"
              onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}
            >
              <Play className="w-4 h-4" />
              <span>Watch Demo</span>
            </button>
          </motion.div>

          {/* Scroll indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="absolute bottom-12 left-1/2 -translate-x-1/2"
          >
            <motion.div
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="flex flex-col items-center gap-2 text-text-muted cursor-pointer"
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
            >
              <span className="text-xs uppercase tracking-[0.2em]">Discover</span>
              <ChevronDown className="w-5 h-5" />
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      {/* ========== FEATURED CHARACTERS ========== */}
      <section id="demo" className="py-32 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-bg-primary via-bg-secondary/50 to-bg-primary" />
        
        <div className="container-app relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <span className="text-accent-primary text-sm font-medium uppercase tracking-[0.2em]">
              Meet the Characters
            </span>
            <h2 className="font-display text-4xl md:text-5xl font-light mt-4 mb-6">
              Conversations That <span className="italic text-gradient">Transcend</span> Pages
            </h2>
            <p className="text-text-secondary text-lg max-w-2xl mx-auto">
              From classic literature to modern fiction, every character awaits with their unique voice, 
              memories, and perspective.
            </p>
          </motion.div>

          {/* Character Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-10">
            {FEATURED_CHARACTERS.map((character, index) => (
              <motion.div
                key={character.name}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.15 }}
                className="group"
              >
                <div className="bento-card p-7 h-full group cursor-pointer">
                  {/* Character Image */}
                  <div className="relative mb-6 overflow-hidden rounded-2xl aspect-square bg-gradient-to-br from-bg-tertiary to-bg-secondary flex items-center justify-center p-8 group-hover:shadow-2xl transition-all duration-500">
                    <img
                      src={character.image}
                      alt={character.name}
                      className="w-full h-full object-contain transition-all duration-700 group-hover:scale-110 group-hover:brightness-110"
                    />
                    <div className="absolute bottom-4 left-4 right-4 transform transition-all duration-500 group-hover:translate-y-0 group-hover:opacity-100 opacity-0 translate-y-2">
                      <span className="inline-block px-4 py-1.5 text-xs font-medium bg-bg-secondary/95 backdrop-blur-md border border-border/50 rounded-full text-text-primary shadow-lg">
                        {character.book}
                      </span>
                    </div>
                    {/* Hover overlay gradient */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  </div>

                  {/* Character Info */}
                  <div className="space-y-3">
                    <h3 className="font-display text-2xl font-medium text-text-primary group-hover:text-accent-primary transition-colors duration-300">
                      {character.name}
                    </h3>
                    <p className="font-literary text-text-secondary italic leading-relaxed line-clamp-3 group-hover:text-text-primary transition-colors duration-300">
                      "{character.quote}"
                    </p>

                    <motion.button
                      className="w-full btn-ghost text-sm flex items-center justify-center gap-2 group-hover:border-accent-primary group-hover:text-accent-primary transition-all duration-300"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <MessageCircle className="w-4 h-4" />
                      Start Conversation
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ========== BENTO FEATURES GRID ========== */}
      <section id="features" className="py-32 relative">
        <div className="container-app">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <span className="text-accent-secondary text-sm font-medium uppercase tracking-[0.2em]">
              How It Works
            </span>
            <h2 className="font-display text-4xl md:text-5xl font-light mt-4">
              Magic in <span className="italic text-gradient-aurora">Three Steps</span>
            </h2>
          </motion.div>

          {/* Bento Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 scroll-stagger">
            {/* Large feature card */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="md:col-span-2 lg:col-span-2"
            >
              <div className="bento-card p-8 h-full relative overflow-hidden">
                <div className="relative z-10">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center mb-6">
                    <BookOpen className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="font-display text-3xl font-medium text-text-primary mb-4">
                    Upload Any Book
                  </h3>
                  <p className="text-text-secondary text-lg mb-6 max-w-lg">
                    Simply drag and drop your PDF. Our AI reads, understands, and extracts 
                    every character's personality, voice, and relationships.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {["PDF", "EPUB", "Any Genre", "Any Length"].map((tag) => (
                      <span key={tag} className="px-3 py-1 text-sm bg-bg-tertiary rounded-full text-text-muted">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                {/* Background image */}
                <div className="absolute right-0 bottom-0 w-1/2 h-full opacity-20">
                  <Image
                    src={IMAGES.bookStack}
                    alt="Books"
                    fill
                    className="object-cover object-left"
                  />
                </div>
              </div>
            </motion.div>

            {/* Smaller cards */}
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.7, delay: 0.1, ease: "easeOut" }}
            >
              <div className="bento-card p-6 h-full">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center mb-5">
                  <Users className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-display text-xl font-medium text-text-primary mb-3">
                  Discover Characters
                </h3>
                <p className="text-text-secondary">
                  Watch as characters emerge from your book, each with their complete backstory and personality.
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
            >
              <div className="bento-card p-6 h-full">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center mb-5">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-display text-xl font-medium text-text-primary mb-3">
                  Real-Time Chat
                </h3>
                <p className="text-text-secondary">
                  Streaming responses that feel natural. Characters remember context and respond authentically.
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
            >
              <div className="bento-card p-6 h-full">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center mb-5">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-display text-xl font-medium text-text-primary mb-3">
                  Private & Secure
                </h3>
                <p className="text-text-secondary">
                  Your books and conversations are encrypted. Your literary world stays yours.
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========== IMMERSIVE SHOWCASE ========== */}
      <section className="py-32 relative overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          <Image
            src={IMAGES.oldLibrary}
            alt="Library atmosphere"
            fill
            className="object-cover opacity-20"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-bg-primary via-bg-primary/90 to-bg-primary" />
        </div>

        <div className="container-app relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            {/* Left - Text */}
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <span className="text-accent-primary text-sm font-medium uppercase tracking-[0.2em]">
                The Experience
              </span>
              <h2 className="font-display text-4xl md:text-5xl font-light mt-4 mb-6">
                Not Just Chat. <br/>
                <span className="italic text-gradient">Literary Immersion.</span>
              </h2>
              <p className="text-text-secondary text-lg mb-8 leading-relaxed">
                Every character remembers their story, their relationships, their growth. 
                Ask Hamlet about his father. Debate philosophy with Raskolnikov. 
                Seek advice from Gandalf. The pages come alive.
              </p>
              
              <div className="space-y-4">
                {[
                  "Characters speak in their authentic voice",
                  "Context-aware conversations that remember",
                  "Explore 'what if' scenarios and alternate endings",
                  "Relationship maps between characters"
                ].map((feature, i) => (
                  <motion.div
                    key={feature}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-6 h-6 rounded-full bg-accent-primary/20 flex items-center justify-center">
                      <Sparkles className="w-3 h-3 text-accent-primary" />
                    </div>
                    <span className="text-text-secondary">{feature}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Right - Chat Preview */}
            <motion.div
              initial={{ opacity: 0, x: 60, scale: 0.95 }}
              whileInView={{ opacity: 1, x: 0, scale: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            >
              <div className="glass-strong rounded-3xl p-6 shadow-2xl">
                {/* Chat header */}
                <div className="flex items-center gap-4 pb-4 border-b border-border mb-6">
                  <div className="avatar-ring">
                    <Image
                      src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&q=85"
                      alt="Sherlock"
                      width={48}
                      height={48}
                      className="rounded-full"
                    />
                  </div>
                  <div>
                    <h4 className="font-display text-lg font-medium text-text-primary">
                      Sherlock Holmes
                    </h4>
                    <p className="text-xs text-accent-primary flex items-center gap-1">
                      <span className="w-2 h-2 bg-accent-primary rounded-full animate-pulse" />
                      Active now
                    </p>
                  </div>
                </div>

                {/* Messages */}
                <div className="space-y-4 mb-6">
                  <div className="flex justify-end">
                    <div className="chat-bubble-user px-5 py-3 max-w-[80%]">
                      <p className="text-sm">How do you approach a seemingly impossible case?</p>
                    </div>
                  </div>
                  
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0">
                      <Image
                        src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&q=85"
                        alt="Sherlock"
                        width={32}
                        height={32}
                        className="object-cover"
                      />
                    </div>
                    <div className="chat-bubble-assistant px-5 py-3 max-w-[85%]">
                      <p className="font-literary text-sm text-text-primary leading-relaxed">
                        "The world is full of obvious things which nobody by any chance ever observes. 
                        I begin where most would end — with the smallest details others dismiss as trivial. 
                        A thread, a footprint, the way dust settles. These are the witnesses that never lie."
                      </p>
                    </div>
                  </div>
                </div>

                {/* Input */}
                <div className="flex gap-3 items-center">
                  <input
                    type="text"
                    placeholder="Ask anything..."
                    className="flex-1 bg-bg-tertiary border border-border rounded-xl px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary"
                    disabled
                  />
                  <button className="w-11 h-11 rounded-xl bg-gradient-to-r from-accent-primary to-purple-600 flex items-center justify-center">
                    <ArrowRight className="w-5 h-5 text-white" />
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========== TESTIMONIALS ========== */}
      <section id="testimonials" className="py-40 relative">
        <div className="container-app">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <span className="text-accent-secondary text-sm font-medium uppercase tracking-[0.2em]">
              What Readers Say
            </span>
            <h2 className="font-display text-4xl md:text-5xl font-light mt-4 mb-6">
              Stories from Our <span className="italic text-gradient-aurora">Community</span>
            </h2>
            <p className="text-text-secondary text-lg max-w-2xl mx-auto">
              Join thousands who've discovered a deeper connection with literature
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto scroll-stagger">
            {TESTIMONIALS.map((testimonial, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 50, scale: 0.9 }}
                whileInView={{ opacity: 1, y: 0, scale: 1 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{
                  delay: i * 0.1,
                  duration: 0.7,
                  ease: "easeOut",
                  type: "spring",
                  stiffness: 100
                }}
                className="group"
              >
                <div className="bento-card p-8 h-full flex flex-col hover:border-accent-primary/30 transition-colors">
                  <div className="flex gap-1 mb-6">
                    {[...Array(5)].map((_, j) => (
                      <Star 
                        key={j} 
                        className="w-5 h-5 text-accent-secondary fill-accent-secondary transition-transform group-hover:scale-110"
                        style={{ transitionDelay: `${j * 50}ms` }}
                      />
                    ))}
                  </div>
                  <blockquote className="font-literary text-text-secondary leading-relaxed mb-8 flex-grow text-base italic">
                    "{testimonial.text}"
                  </blockquote>
                  <div className="flex items-center gap-4 pt-6 border-t border-border">
                    <div className="relative">
            <Image
                        src={testimonial.avatar}
                        alt={testimonial.author}
                        width={56}
                        height={56}
                        className="rounded-full ring-2 ring-border group-hover:ring-accent-primary/50 transition-all"
                        quality={100}
                      />
                    </div>
                    <div>
                      <p className="font-display font-medium text-text-primary">{testimonial.author}</p>
                      <p className="text-text-muted text-sm mt-0.5">{testimonial.role}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ========== FINAL CTA ========== */}
      <section className="py-32 relative overflow-hidden">
        {/* Gradient orbs */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[600px]">
          <div className="glow-orb absolute top-0 left-1/4 w-[400px] h-[400px] bg-accent-primary/30" />
          <div className="glow-orb absolute bottom-0 right-1/4 w-[300px] h-[300px] bg-accent-secondary/20" style={{ animationDelay: '2s' }} />
        </div>

        <div className="container-app relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className="mx-auto mb-8">
              <LogoMark size={80} />
            </div>

            <h2 className="font-display text-4xl md:text-6xl font-light mb-6">
              Your Characters <span className="italic text-gradient">Await</span>
            </h2>
            <p className="text-text-secondary text-lg max-w-xl mx-auto mb-10">
              Join thousands who've discovered a new way to experience literature.
              Start your journey today — it's free.
            </p>

            <Link href="/login">
              <button className="btn-magic text-lg px-10 py-4 flex items-center gap-3 mx-auto group">
                <Sparkles className="w-5 h-5" />
                <span>Start Free</span>
                <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              </button>
            </Link>

            <p className="text-text-muted text-sm mt-6">
              No credit card required • Unlimited characters
            </p>
          </motion.div>
        </div>
      </section>

      {/* ========== FOOTER ========== */}
      <footer className="relative border-t border-border bg-bg-secondary/30">
        <div className="container-app py-20">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
            {/* Brand */}
            <div className="md:col-span-1">
              <Logo size="lg" animated={false} className="mb-6" />
              <p className="text-text-secondary text-sm leading-relaxed max-w-xs">
                Step into your favorite stories. Have conversations with characters that feel impossibly real.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="font-display font-semibold text-text-primary mb-4">Product</h4>
              <ul className="space-y-3 text-sm">
                <li>
                  <Link href="/features" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Features
                  </Link>
                </li>
                <li>
                  <Link href="/pricing" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href="/demo" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Demo
                  </Link>
                </li>
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="font-display font-semibold text-text-primary mb-4">Company</h4>
              <ul className="space-y-3 text-sm">
                <li>
                  <Link href="/about" className="text-text-secondary hover:text-accent-primary transition-colors">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="/blog" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Blog
                  </Link>
                </li>
                <li>
                  <Link href="/contact" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="font-display font-semibold text-text-primary mb-4">Legal</h4>
              <ul className="space-y-3 text-sm">
                <li>
                  <Link href="/privacy" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link href="/terms" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Terms
                  </Link>
                </li>
                <li>
                  <Link href="/security" className="text-text-secondary hover:text-accent-primary transition-colors">
                    Security
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-text-muted text-sm">
              © {new Date().getFullYear()} Character Chat. Made with <span className="text-rose-400">♥</span> by <span className="text-accent-primary font-medium">Bhavik</span>.
            </p>
            <div className="flex items-center gap-6">
              <a 
                href="https://twitter.com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-text-muted hover:text-accent-primary transition-colors text-sm"
                aria-label="Twitter"
              >
                Twitter
          </a>
          <a
                href="https://github.com" 
            target="_blank"
            rel="noopener noreferrer"
                className="text-text-muted hover:text-accent-primary transition-colors text-sm"
                aria-label="GitHub"
          >
                GitHub
          </a>
            </div>
          </div>
        </div>
      </footer>
      </main>
  );
}
