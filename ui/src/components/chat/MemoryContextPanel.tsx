"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MdKeyboardArrowDown, MdMemory } from "react-icons/md";
import { cn } from "@/lib/utils";
import type { MemoryDocumentRef } from "@/types/chat";

interface MemoryContextPanelProps {
  documents: MemoryDocumentRef[];
}

const TRUST_BADGE: Record<string, { label: string; className: string }> = {
  admin_approved: {
    label: "admin",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  system_seeded: {
    label: "system",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  user_authored: {
    label: "user",
    className: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  },
  agent_draft: {
    label: "draft",
    className: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  },
};

function TrustBadge({ level }: { level: string }) {
  const badge = TRUST_BADGE[level] ?? {
    label: level,
    className: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium border",
        badge.className
      )}
    >
      {badge.label}
    </span>
  );
}

export function MemoryContextPanel({ documents }: MemoryContextPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const panelId = "memory-context-panel";

  if (!documents || documents.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg border border-zinc-800/50 bg-zinc-900/30 overflow-hidden">
      <button
        onClick={() => setIsExpanded((v) => !v)}
        aria-expanded={isExpanded}
        aria-controls={panelId}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-zinc-800/30 transition-colors"
      >
        <MdMemory className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
        <span className="text-xs text-zinc-500 flex-1">
          Memory used ({documents.length})
        </span>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <MdKeyboardArrowDown className="w-3.5 h-3.5 text-zinc-600" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <div className="px-3 pb-2 space-y-1.5 overflow-y-auto max-h-80">
              {documents.map((doc) => (
                <div
                  key={doc.document_id}
                  className="flex items-start gap-2 py-1.5 border-t border-zinc-800/40 first:border-t-0"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <TrustBadge level={doc.trust_level} />
                      <span className="text-xs text-zinc-500 font-medium truncate">
                        {doc.store_slug}
                      </span>
                    </div>
                    <p
                      className="text-xs text-zinc-400 mt-0.5 font-mono truncate"
                      title={doc.path}
                    >
                      {doc.path}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
