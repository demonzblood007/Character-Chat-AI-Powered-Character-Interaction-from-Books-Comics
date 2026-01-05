"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { checkAuth } = useAuthStore();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Try to check auth but don't block rendering
    checkAuth().finally(() => setIsReady(true));
    
    // Set ready after a short delay even if check fails (demo mode)
    const timeout = setTimeout(() => setIsReady(true), 500);
    return () => clearTimeout(timeout);
  }, [checkAuth]);

  // Show loading briefly
  if (!isReady) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Allow demo viewing without strict auth (for preview)
  return <>{children}</>;
}

