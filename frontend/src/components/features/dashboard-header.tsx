"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, Settings, LogOut, User, ChevronDown } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Avatar, Button } from "@/components/ui";
import { Logo, LogoMark } from "@/components/ui/logo";
import { useAuthStore } from "@/stores/auth-store";

export function DashboardHeader() {
  const { user, logout } = useAuthStore();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-50 glass-strong border-b border-border">
      <div className="container-app">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Logo size="md" animated={false} className="hidden sm:flex" />
              <LogoMark size={40} className="sm:hidden" />
            </motion.div>
          </Link>

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Notifications */}
            <button className="relative p-2.5 rounded-xl hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-all">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-accent-secondary rounded-full animate-pulse" />
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="flex items-center gap-3 p-2 rounded-xl hover:bg-bg-tertiary transition-all"
              >
                <Avatar
                  src={user?.avatar_url}
                  name={user?.name || "User"}
                  size="sm"
                />
                <div className="hidden md:block text-left">
                  <p className="text-sm font-medium text-text-primary">
                    {user?.name || "User"}
                  </p>
                  <p className="text-xs text-text-muted capitalize">
                    {user?.subscription.tier || "Free"} Plan
                  </p>
                </div>
                <ChevronDown className={`w-4 h-4 text-text-muted transition-transform ${isMenuOpen ? "rotate-180" : ""}`} />
              </button>

              {/* Dropdown Menu */}
              <AnimatePresence>
                {isMenuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setIsMenuOpen(false)}
                    />
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-56 rounded-2xl glass-strong shadow-2xl overflow-hidden z-50"
                    >
                      {/* User info */}
                      <div className="p-4 border-b border-border">
                        <p className="font-medium text-text-primary">{user?.name}</p>
                        <p className="text-sm text-text-muted">{user?.email}</p>
                      </div>

                      {/* Menu items */}
                      <div className="p-2">
                        <Link
                          href="/settings"
                          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
                          onClick={() => setIsMenuOpen(false)}
                        >
                          <User className="w-4 h-4" />
                          <span>Profile</span>
                        </Link>
                        <Link
                          href="/settings"
                          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
                          onClick={() => setIsMenuOpen(false)}
                        >
                          <Settings className="w-4 h-4" />
                          <span>Settings</span>
                        </Link>
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-rose-400 hover:bg-rose-500/10 transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
