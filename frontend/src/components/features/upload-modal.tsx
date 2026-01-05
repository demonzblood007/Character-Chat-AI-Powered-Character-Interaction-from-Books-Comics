"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Upload, FileText, CheckCircle, AlertCircle, Sparkles } from "lucide-react";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui";
import { useBooksStore } from "@/stores/books-store";
import { formatFileSize } from "@/lib/utils";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UploadModal({ isOpen, onClose }: UploadModalProps) {
  const { uploadBook, uploadProgress, isLoading } = useBooksStore();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [error, setError] = useState<string>("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      setFile(selectedFile);
      setStatus("idle");
      setError("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
    disabled: isLoading,
  });

  const handleUpload = async () => {
    if (!file) return;

    setStatus("uploading");
    setError("");

    try {
      await uploadBook(file);
      setStatus("success");
      
      // Close modal after success
      setTimeout(() => {
        handleClose();
      }, 2000);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setFile(null);
      setStatus("idle");
      setError("");
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={handleClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg glass-modal rounded-2xl z-50 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div>
                <h2 className="font-display text-xl font-bold text-text-primary">
                  Upload Book
                </h2>
                <p className="text-sm text-text-secondary mt-1">
                  Add a new book to your library
                </p>
              </div>
              <button
                onClick={handleClose}
                disabled={isLoading}
                className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors text-text-muted hover:text-text-primary disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6">
              {status !== "success" ? (
                <>
                  {/* Dropzone */}
                  <div
                    {...getRootProps()}
                    className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                      isDragActive
                        ? "border-accent-primary bg-accent-primary/5"
                        : file
                        ? "border-green-500/50 bg-green-500/5"
                        : "border-border hover:border-accent-primary/50 hover:bg-bg-tertiary"
                    } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <input {...getInputProps()} />
                    
                    <motion.div
                      animate={isDragActive ? { scale: 1.05 } : { scale: 1 }}
                      className="flex flex-col items-center"
                    >
                      {file ? (
                        <>
                          <div className="w-16 h-16 rounded-xl bg-green-500/10 flex items-center justify-center mb-4">
                            <FileText className="w-8 h-8 text-green-500" />
                          </div>
                          <p className="font-medium text-text-primary mb-1">
                            {file.name}
                          </p>
                          <p className="text-sm text-text-muted">
                            {formatFileSize(file.size)}
                          </p>
                        </>
                      ) : (
                        <>
                          <div className="w-16 h-16 rounded-xl bg-bg-tertiary flex items-center justify-center mb-4">
                            <Upload className={`w-8 h-8 ${isDragActive ? "text-accent-primary" : "text-text-muted"}`} />
                          </div>
                          <p className="font-medium text-text-primary mb-1">
                            {isDragActive ? "Drop your book here" : "Drag & drop your book"}
                          </p>
                          <p className="text-sm text-text-muted">
                            or click to browse (PDF, max 50MB)
                          </p>
                        </>
                      )}
                    </motion.div>
                  </div>

                  {/* Upload progress */}
                  {status === "uploading" && (
                    <div className="mt-6">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-text-secondary">Uploading...</span>
                        <span className="text-sm font-medium text-accent-primary">{uploadProgress}%</span>
                      </div>
                      <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary"
                          initial={{ width: 0 }}
                          animate={{ width: `${uploadProgress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error message */}
                  {status === "error" && (
                    <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-red-400">Upload failed</p>
                        <p className="text-sm text-red-400/80">{error}</p>
                      </div>
                    </div>
                  )}

                  {/* Info */}
                  <div className="mt-6 p-4 bg-bg-tertiary rounded-xl">
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-5 h-5 text-accent-secondary flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm text-text-primary font-medium">
                          What happens next?
                        </p>
                        <p className="text-sm text-text-secondary mt-1">
                          We'll analyze your book, extract all characters, and map their 
                          relationships. This usually takes 1-3 minutes.
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                /* Success state */
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-8"
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 200, damping: 15 }}
                    className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-500/10 flex items-center justify-center"
                  >
                    <CheckCircle className="w-10 h-10 text-green-500" />
                  </motion.div>
                  <h3 className="font-display text-xl font-bold text-text-primary mb-2">
                    Upload Complete! 🎭
                  </h3>
                  <p className="text-text-secondary">
                    Your characters are being discovered...
                  </p>
                </motion.div>
              )}
            </div>

            {/* Footer */}
            {status !== "success" && (
              <div className="flex items-center justify-end gap-3 p-6 border-t border-border bg-bg-tertiary/30">
                <Button
                  variant="ghost"
                  onClick={handleClose}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUpload}
                  disabled={!file || isLoading}
                  isLoading={status === "uploading"}
                  leftIcon={<Upload className="w-4 h-4" />}
                >
                  Upload Book
                </Button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

