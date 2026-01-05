"use client";

import { motion } from "framer-motion";
import { Upload, Users, MessageSquare, Sparkles, Network, Shield } from "lucide-react";
import { Card } from "@/components/ui";

const features = [
  {
    icon: Upload,
    title: "Upload Any Book",
    description: "Simply drag and drop your favorite PDF. We support novels, comics, and any text-based stories.",
    gradient: "from-violet-500 to-purple-600",
  },
  {
    icon: Users,
    title: "Meet Every Character",
    description: "Our AI extracts and understands every character's personality, voice, and story arc.",
    gradient: "from-amber-500 to-orange-600",
  },
  {
    icon: MessageSquare,
    title: "Natural Conversations",
    description: "Chat naturally with characters who remember context and respond in their authentic voice.",
    gradient: "from-emerald-500 to-teal-600",
  },
  {
    icon: Network,
    title: "Relationship Maps",
    description: "Visualize how characters connect. Explore alliances, rivalries, and hidden connections.",
    gradient: "from-blue-500 to-cyan-600",
  },
  {
    icon: Sparkles,
    title: "Living Stories",
    description: "Characters evolve as you chat. Create new storylines and explore 'what if' scenarios.",
    gradient: "from-pink-500 to-rose-600",
  },
  {
    icon: Shield,
    title: "Your Library, Private",
    description: "Your books and conversations are encrypted and private. Your stories stay yours.",
    gradient: "from-slate-500 to-gray-600",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.43, 0.13, 0.23, 0.96] as const, // easeOut cubic bezier
    },
  },
};

export function Features() {
  return (
    <section id="features" className="py-32 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-bg-secondary via-bg-primary to-bg-secondary" />
      
      {/* Decorative elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-accent-primary/5 blur-[120px] rounded-full" />
      
      <div className="container-app relative z-10">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-accent-primary font-medium text-sm uppercase tracking-widest">
            Features
          </span>
          <h2 className="font-display text-4xl md:text-5xl font-bold mt-4 mb-6">
            Your Personal{" "}
            <span className="text-gradient">Story Universe</span>
          </h2>
          <p className="text-text-secondary text-lg max-w-2xl mx-auto">
            Everything you need to bring your favorite books to life and create 
            unforgettable conversations with beloved characters.
          </p>
        </motion.div>

        {/* Features grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feature, index) => (
            <motion.div key={index} variants={itemVariants}>
              <Card
                className="h-full group"
                glow
              >
                {/* Icon */}
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                
                {/* Content */}
                <h3 className="font-display text-xl font-semibold text-text-primary mb-3">
                  {feature.title}
                </h3>
                <p className="text-text-secondary leading-relaxed">
                  {feature.description}
                </p>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

