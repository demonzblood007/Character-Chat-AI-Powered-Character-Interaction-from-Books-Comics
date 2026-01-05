"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui";
import { Logo, LogoMark } from "@/components/ui/logo";
import { useAuthStore } from "@/stores/auth-store";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { login, isLoading, isAuthenticated } = useAuthStore();
  const router = useRouter();

  // Redirect if already authenticated (check persisted state only)
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, router]);

  return (
    <div className="min-h-screen flex">
      {/* Left side - Decorative */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-bg-secondary">
        {/* Animated background */}
        <div className="absolute inset-0">
          <motion.div
            className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full bg-accent-primary/20 blur-[100px]"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.3, 0.5, 0.3],
            }}
            transition={{ duration: 8, repeat: Infinity }}
          />
          <motion.div
            className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-accent-secondary/15 blur-[80px]"
            animate={{
              scale: [1.2, 1, 1.2],
              opacity: [0.2, 0.4, 0.2],
            }}
            transition={{ duration: 10, repeat: Infinity }}
          />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center items-center p-12 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="mx-auto mb-8">
              <Logo size="xl" animated={true} />
            </div>
            
            <h1 className="font-display text-4xl font-bold mb-4">
              Welcome to{" "}
              <span className="text-gradient">Your Stories</span>
            </h1>
            
            <p className="text-text-secondary text-lg max-w-md mb-8">
              Step into a world where your favorite book characters come alive. 
              Upload any story and start conversations that feel real.
            </p>

            {/* Floating quotes */}
            <div className="space-y-4">
              {[
                { character: "Batman", quote: "It's not who I am underneath, but what I do that defines me." },
                { character: "Hermione", quote: "Books! And cleverness! There are more important things..." },
              ].map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + index * 0.2 }}
                  className="bg-bg-tertiary/50 backdrop-blur-sm border border-border rounded-xl p-4 text-left"
                >
                  <p className="font-literary text-text-secondary italic text-sm">
                    "{item.quote}"
                  </p>
                  <p className="text-accent-primary text-xs mt-2 font-medium">
                    — {item.character}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-bg-primary">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden mb-8 text-center">
            <Link href="/">
              <Logo size="lg" animated={false} className="justify-center" />
            </Link>
          </div>

          <div className="text-center mb-8">
            <h2 className="font-display text-3xl font-bold text-text-primary mb-2">
              Enter Your Story
            </h2>
            <p className="text-text-secondary">
              Sign in to start chatting with your favorite characters
            </p>
          </div>

          {/* Google Sign In Button */}
          <Button
            variant="secondary"
            size="lg"
            className="w-full mb-6 py-4"
            onClick={login}
            isLoading={isLoading}
            leftIcon={
              <Image
                src="https://www.google.com/favicon.ico"
                alt="Google"
                width={20}
                height={20}
                className="rounded"
                unoptimized
              />
            }
          >
            Continue with Google
          </Button>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-bg-primary text-text-muted text-sm">
                Secure authentication
              </span>
            </div>
          </div>

          {/* Features */}
          <div className="space-y-3 mb-8">
            {[
              "Upload unlimited books",
              "Chat with any character",
              "Your conversations are private",
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + index * 0.1 }}
                className="flex items-center gap-3 text-text-secondary"
              >
                <Sparkles className="w-4 h-4 text-accent-primary" />
                <span className="text-sm">{feature}</span>
              </motion.div>
            ))}
          </div>

          {/* Terms */}
          <p className="text-center text-text-muted text-xs">
            By continuing, you agree to our{" "}
            <Link href="/terms" className="text-accent-primary hover:underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-accent-primary hover:underline">
              Privacy Policy
            </Link>
          </p>

          {/* Back link */}
          <div className="mt-8 text-center">
            <Link
              href="/"
              className="text-text-secondary hover:text-accent-primary transition-colors text-sm"
            >
              ← Back to home
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

