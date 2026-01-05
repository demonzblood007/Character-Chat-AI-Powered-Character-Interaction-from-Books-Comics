"use client";

import { motion } from "framer-motion";
import { Book, BookOpen, Library, Bookmark, ScrollText } from "lucide-react";

const books = [
  { Icon: Book, delay: 0, x: "10%", y: "20%", rotate: -15, size: 40 },
  { Icon: BookOpen, delay: 0.5, x: "85%", y: "15%", rotate: 12, size: 48 },
  { Icon: Library, delay: 1, x: "5%", y: "60%", rotate: -8, size: 36 },
  { Icon: Bookmark, delay: 1.5, x: "90%", y: "55%", rotate: 20, size: 32 },
  { Icon: ScrollText, delay: 2, x: "15%", y: "85%", rotate: -5, size: 44 },
  { Icon: Book, delay: 2.5, x: "80%", y: "80%", rotate: 15, size: 38 },
];

export function FloatingBooks() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {books.map((book, index) => (
        <motion.div
          key={index}
          className="absolute"
          style={{ left: book.x, top: book.y }}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: book.delay }}
        >
          <motion.div
            animate={{
              y: [-10, 10, -10],
              rotate: [book.rotate - 5, book.rotate + 5, book.rotate - 5],
            }}
            transition={{
              duration: 4 + index,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          >
            <book.Icon
              size={book.size}
              className="text-accent-primary/20"
              strokeWidth={1.5}
            />
          </motion.div>
        </motion.div>
      ))}
    </div>
  );
}

