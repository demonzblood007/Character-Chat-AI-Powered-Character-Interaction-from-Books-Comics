"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { BookOpen, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { auth } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setUser } = useAuthStore();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const handleCallback = async () => {
      // Check for error first
      const errorParam = searchParams.get("error");
      if (errorParam) {
        setStatus("error");
        setError(errorParam);
        return;
      }

      // Backend redirects with tokens in URL (GET /auth/google/callback handles OAuth exchange)
      const accessToken = searchParams.get("access_token");
      const refreshToken = searchParams.get("refresh_token");

      if (accessToken && refreshToken) {
        try {
          // Store tokens
          auth.setTokens({
            access_token: accessToken,
            refresh_token: refreshToken,
            expires_in: 900, // 15 minutes default, will be refreshed if needed
          });

          // Get user info
          const user = await auth.getCurrentUser();
          if (user) {
            setUser(user);
            setStatus("success");
            
            // Redirect to dashboard after a short delay
            setTimeout(() => {
              router.push("/dashboard");
            }, 1500);
          } else {
            throw new Error("Failed to get user information");
          }
        } catch (err) {
          console.error("Auth callback error:", err);
          setStatus("error");
          setError(err instanceof Error ? err.message : "Authentication failed");
        }
        return;
      }

      // Fallback: try code/state flow (for POST callback endpoint)
      const code = searchParams.get("code");
      const state = searchParams.get("state");

      if (code && state) {
        try {
          const user = await auth.handleCallback(code, state);
          setUser(user);
          setStatus("success");
          
          setTimeout(() => {
            router.push("/dashboard");
          }, 1500);
        } catch (err) {
          console.error("Auth callback error:", err);
          setStatus("error");
          setError(err instanceof Error ? err.message : "Authentication failed");
        }
        return;
      }

      // No valid parameters
      setStatus("error");
      setError("Missing authentication parameters");
    };

    handleCallback();
  }, [searchParams, setUser, router]);

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md"
      >
        {/* Logo */}
        <motion.div
          className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-gradient-to-br from-accent-primary to-indigo-600 flex items-center justify-center"
          animate={status === "loading" ? { rotate: 360 } : {}}
          transition={{ duration: 2, repeat: status === "loading" ? Infinity : 0, ease: "linear" }}
        >
          <BookOpen className="w-10 h-10 text-white" />
        </motion.div>

        {/* Loading state */}
        {status === "loading" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <Loader2 className="w-5 h-5 text-accent-primary animate-spin" />
              <h2 className="font-display text-2xl font-bold text-text-primary">
                Signing you in...
              </h2>
            </div>
            <p className="text-text-secondary">
              Just a moment while we prepare your library
            </p>
            
            {/* Animated dots */}
            <div className="flex justify-center gap-2 mt-6">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 bg-accent-primary rounded-full"
                  animate={{ y: [0, -8, 0] }}
                  transition={{
                    duration: 0.6,
                    repeat: Infinity,
                    delay: i * 0.15,
                  }}
                />
              ))}
            </div>
          </motion.div>
        )}

        {/* Success state */}
        {status === "success" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
              className="mb-6"
            >
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
            </motion.div>
            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
              Welcome! 🎭
            </h2>
            <p className="text-text-secondary mb-4">
              Your characters are waiting for you
            </p>
            <p className="text-text-muted text-sm">
              Redirecting to your library...
            </p>
          </motion.div>
        )}

        {/* Error state */}
        {status === "error" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
              className="mb-6"
            >
              <XCircle className="w-16 h-16 text-red-500 mx-auto" />
            </motion.div>
            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
              Authentication Failed
            </h2>
            <p className="text-text-secondary mb-6">
              {error || "Something went wrong. Please try again."}
            </p>
            <Button
              onClick={() => router.push("/login")}
              leftIcon={<BookOpen className="w-4 h-4" />}
            >
              Try Again
            </Button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
