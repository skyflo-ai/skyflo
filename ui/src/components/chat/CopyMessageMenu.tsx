"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MdCheck, MdContentCopy } from "react-icons/md";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/types/chat";

interface CopyMessageMenuProps {
  message: ChatMessage;
}

function extractContent(message: ChatMessage): {
  markdown: string;
  plainText: string;
} {
  const segments = message.segments || [];
  const markdown = segments
    .filter((seg) => seg.kind === "text")
    .map((seg) => seg.text)
    .join("\n\n");

  const plainText = markdown
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    .replace(/~~(.+?)~~/g, "$1")
    .replace(/`{3}[\s\S]*?`{3}/g, (match) =>
      match.replace(/`{3}\w*\n?/g, "").trim()
    )
    .replace(/`(.+?)`/g, "$1")
    .replace(/\[(.+?)\]\(.+?\)/g, "$1")
    .replace(/!\[.*?\]\(.+?\)/g, "")
    .replace(/^>\s+/gm, "")
    .replace(/^[-*+]\s+/gm, "")
    .replace(/^\d+\.\s+/gm, "")
    .replace(/^---+$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return { markdown, plainText };
}

export function CopyMessageMenu({ message }: CopyMessageMenuProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState<"text" | "markdown" | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const handleCopy = useCallback(
    async (mode: "text" | "markdown") => {
      const { markdown, plainText } = extractContent(message);
      const content = mode === "markdown" ? markdown : plainText;
      try {
        await navigator.clipboard.writeText(content);
        setCopied(mode);
        setTimeout(() => {
          setCopied(null);
          setOpen(false);
        }, 1200);
      } catch {
        setOpen(false);
      }
    },
    [message],
  );

  return (
    <div className="relative inline-flex" ref={menuRef}>
      <button
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "p-1.5 rounded-md transition-colors duration-150",
          "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60",
          open && "text-zinc-300 bg-zinc-800/60"
        )}
        aria-label="Copy message"
      >
        <MdContentCopy className="h-4 w-4" />
      </button>

      {open && (
        <div
          className={cn(
            "absolute bottom-full left-0 mb-1 z-50",
            "w-max py-1 rounded-lg",
            "bg-zinc-900 border border-zinc-800/60",
            "shadow-lg shadow-black/40",
            "animate-in fade-in-0 zoom-in-95 duration-150"
          )}
        >
          <button
            onClick={() => handleCopy("text")}
            className={cn(
              "w-full flex items-center gap-2.5 px-3 py-2 text-sm whitespace-nowrap",
              "text-zinc-300 hover:bg-zinc-800/60 hover:text-white",
              "transition-colors duration-100"
            )}
          >
            {copied === "text" ? (
              <MdCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            ) : (
              <MdContentCopy className="h-4 w-4 text-zinc-500 shrink-0" />
            )}
            Copy text
          </button>
          <button
            onClick={() => handleCopy("markdown")}
            className={cn(
              "w-full flex items-center gap-2.5 px-3 py-2 text-sm whitespace-nowrap",
              "text-zinc-300 hover:bg-zinc-800/60 hover:text-white",
              "transition-colors duration-100"
            )}
          >
            {copied === "markdown" ? (
              <MdCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            ) : (
              <MdContentCopy className="h-4 w-4 text-zinc-500 shrink-0" />
            )}
            Copy markdown
          </button>
        </div>
      )}
    </div>
  );
}
