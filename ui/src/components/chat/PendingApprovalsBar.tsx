"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AiOutlineStop } from "react-icons/ai";

import { MdAccessTime, MdDoneAll, MdClose } from "react-icons/md";
import { cn } from "@/lib/utils";

interface PendingApprovalsBarProps {
  count: number;
  onAction?: (decision: "approve" | "deny") => void;
  progress?: {
    done: number;
    total: number;
    decision: "approve" | "deny";
  } | null;
  disabled?: boolean;
}

export function PendingApprovalsBar({
  count,
  onAction,
  progress,
  disabled = false,
}: PendingApprovalsBarProps) {
  const running = !!progress;
  const done = progress?.done ?? 0;
  const total = progress?.total ?? count;
  const decision = progress?.decision ?? "approve";

  return (
    <AnimatePresence initial={false}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        className={cn("w-full", running && "animate-pulse")}
      >
        <div className="py-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2 text-sm text-[#c9d4e2]">
            <MdAccessTime className="w-4 h-4" />
            <span>
              {running
                ? `${
                    decision === "approve" ? "Approving" : "Declining"
                  } ${Math.min(done + 1, total)}/${total}…`
                : `${count} approvals pending`}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onAction?.("approve")}
              disabled={disabled || running}
              className={cn(
                "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium",
                "border border-green-500/30 bg-green-600/10",
                "hover:bg-green-600/20",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              <MdDoneAll className="text-green-300" />
              <span>
                {running && decision === "approve"
                  ? "Approving…"
                  : "Approve all"}
              </span>
            </button>
            <button
              type="button"
              onClick={() => onAction?.("deny")}
              disabled={disabled || running}
              className={cn(
                "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium",
                "border border-red-500/30 bg-red-600/10",
                "hover:bg-red-600/20",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              <AiOutlineStop className="text-red-300" />
              <span>
                {running && decision === "deny" ? "Declining…" : "Decline all"}
              </span>
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
