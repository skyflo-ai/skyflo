"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  useId,
  useMemo,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MdKeyboardArrowRight } from "react-icons/md";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { markdownComponents } from "../ui/markdown-components";

interface ThinkingBlockProps {
  text: string;
  isComplete?: boolean;
  durationMs?: number;
}

const PREVIEW_HEIGHT = 160;
const MAX_EXPANDED_HEIGHT = 480;
const OVERFLOW_CHAR_THRESHOLD = 300;

const contentVariants = {
  collapsed: {
    height: 0,
    opacity: 0,
    overflow: "hidden" as const,
    transition: {
      height: { duration: 0.2, ease: "easeIn" },
      opacity: { duration: 0.1 },
    },
  },
  expanded: {
    height: "auto" as const,
    opacity: 1,
    transition: {
      height: { duration: 0.25, ease: "easeOut" },
      opacity: { duration: 0.15, delay: 0.08 },
    },
  },
};

function formatDuration(ms: number): string {
  if (ms < 0) ms = 0;
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

export function ThinkingBlock({
  text,
  isComplete = false,
  durationMs,
}: ThinkingBlockProps) {
  const [isOpen, setIsOpen] = useState(!isComplete);
  const [showFullContent, setShowFullContent] = useState(false);
  const wasCompleteRef = useRef(isComplete);
  const contentId = useId();

  const hasOverflow = useMemo(
    () => text.length > OVERFLOW_CHAR_THRESHOLD,
    [text],
  );

  useEffect(() => {
    if (isComplete && !wasCompleteRef.current) {
      setIsOpen(false);
      setShowFullContent(false);
      wasCompleteRef.current = true;
    }
  }, [isComplete]);

  const headerLabel = isComplete
    ? `Thought${durationMs ? ` for ${formatDuration(durationMs)}` : ""}`
    : "Thinking";

  const handleToggleContent = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowFullContent((prev) => !prev);
  }, []);

  return (
    <div className="max-w-2xl">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-controls={contentId}
        className={cn(
          "flex w-full items-center gap-1.5 py-1 text-left text-base",
          "text-zinc-500 hover:text-zinc-400 transition-colors",
          "select-none",
        )}
      >
        <motion.div
          animate={{ rotate: isOpen ? 90 : 0 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="shrink-0"
        >
          <MdKeyboardArrowRight className="h-3.5 w-3.5" />
        </motion.div>

        <span
          className={cn(
            "font-medium tracking-wide",
            !isComplete && "thinking-text-shimmer",
          )}
        >
          {headerLabel}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            id={contentId}
            key="thinking-content"
            initial="collapsed"
            animate="expanded"
            exit="collapsed"
            variants={contentVariants}
          >
            <div className="pt-1">
              <div
                className={cn(
                  "overflow-y-auto thinking-scroll transition-[max-height] duration-300 ease-out",
                  hasOverflow && !showFullContent && "thinking-fade",
                )}
                style={{
                  maxHeight: showFullContent
                    ? `${MAX_EXPANDED_HEIGHT}px`
                    : `${PREVIEW_HEIGHT}px`,
                }}
              >
                <div
                  className={cn(
                    "prose prose-invert max-w-none",
                    "prose-p:text-zinc-700 prose-p:leading-relaxed",
                    "prose-headings:text-zinc-700",
                    "prose-strong:text-zinc-600",
                    "prose-code:text-zinc-700",
                    "prose-li:text-zinc-700",
                    "opacity-40",
                  )}
                >
                  <ReactMarkdown
                    className="leading-relaxed text-zinc-700"
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {text}
                  </ReactMarkdown>
                </div>
              </div>

              {hasOverflow && (
                <button
                  type="button"
                  onClick={handleToggleContent}
                  className="mt-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-400 transition-colors"
                >
                  {showFullContent ? "Show less" : "Show more"}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
