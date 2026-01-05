import type { Metadata } from "next";
import { Cormorant_Garamond, DM_Sans, Crimson_Pro, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

// Typography - Elegant & Cinematic
const cormorant = Cormorant_Garamond({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

const dmSans = DM_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const crimsonPro = Crimson_Pro({
  variable: "--font-literary",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});

const jetbrains = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Character Chat | Step Into Your Stories",
  description: "Upload your favorite books and have real conversations with the characters. An immersive AI experience that brings fiction to life.",
  keywords: ["AI chat", "book characters", "interactive fiction", "character AI", "story chat", "literary AI"],
  authors: [{ name: "Character Chat" }],
  openGraph: {
    title: "Character Chat | Step Into Your Stories",
    description: "Upload your favorite books and have real conversations with the characters.",
    type: "website",
    locale: "en_US",
    images: [
      {
        url: "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1200&h=630&fit=crop",
        width: 1200,
        height: 630,
        alt: "Character Chat - Where Stories Come Alive",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Character Chat | Step Into Your Stories",
    description: "Upload your favorite books and have real conversations with the characters.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${cormorant.variable} ${dmSans.variable} ${crimsonPro.variable} ${jetbrains.variable} antialiased`}
      >
        <Providers>
        {children}
        </Providers>
      </body>
    </html>
  );
}
