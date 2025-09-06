"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#030712] p-4 relative overflow-hidden">
      <div className="absolute left-1/2 top-1/3 -translate-y-1/3 -translate-x-1/2 w-[80%] aspect-square opacity-[0.04] pointer-events-none select-none">
        <img
          src="/logo_vector_transparent.png"
          alt=""
          className="w-full h-full object-contain"
        />
      </div>

      <div
        className="absolute inset-0 bg-[linear-gradient(to_right,#1a1a1a_1px,transparent_1px),linear-gradient(to_bottom,#1a1a1a_1px,transparent_1px)] opacity-50"
        style={{
          backgroundSize: "48px 48px",
        }}
      />

      <div className="absolute top-0 -left-4 w-[40rem] h-[40rem] bg-[#00B7FF] rounded-full mix-blend-multiply filter blur-[128px] opacity-[0.08]" />
      <div className="absolute bottom-0 right-0 w-[40rem] h-[40rem] bg-[#0056B3] rounded-full mix-blend-multiply filter blur-[128px] opacity-[0.08]" />

      <div className="w-full max-w-2xl space-y-8 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center space-y-6"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-8xl md:text-9xl font-bold text-transparent bg-gradient-to-r from-[#00B7FF] to-[#06B6D4] bg-clip-text"
          >
            404
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="space-y-2"
          >
            <h2 className="text-2xl font-semibold text-white">
              Page Not Found
            </h2>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="text-center space-y-4"
        >
          <p className="text-slate-400 text-sm">
            Need help with cloud operations?
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Link
              href="/"
              className="text-[#06B6D4] hover:text-[#00B7FF] text-sm  transition-colors"
            >
              Start a new chat
            </Link>
            <span className="text-slate-500 hover:cursor-default">•</span>
            <Link
              href="/history"
              className="text-[#06B6D4] hover:text-[#00B7FF] text-sm  transition-colors"
            >
              View history
            </Link>
            <span className="text-slate-500 hover:cursor-default">•</span>
            <Link
              href="/settings"
              className="text-[#06B6D4] hover:text-[#00B7FF] text-sm  transition-colors"
            >
              Settings
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
