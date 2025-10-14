"use client";

import { MdArrowUpward, MdDelete } from "react-icons/md";

type QueuedItem = { id: string; content: string; timestamp: number };

interface QueuedMessagesBarProps {
  items: QueuedItem[];
  onSubmitNow: (id: string) => void;
  onRemove: (id: string) => void;
}

export function QueuedMessagesBar({
  items,
  onSubmitNow,
  onRemove,
}: QueuedMessagesBarProps) {
  if (!items || items.length === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between text-xs text-[#c8d1de]/80 mb-1">
        <span className="tracking-wide">{items.length} Queued</span>
      </div>
      <div className="flex flex-col">
        {items.map((m) => (
          <div
            key={m.id}
            className="py-2 border-b border-[#1E2D45] last:border-b-0"
            title={m.content}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-[#c9d4e2] truncate">
                {m.content}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => onSubmitNow(m.id)}
                  aria-label="Submit now"
                  title="Submit now"
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border border-green-500/30 bg-green-600/10 hover:bg-green-600/20 focus:outline-none"
                >
                  <MdArrowUpward className="w-4 h-4 text-green-300" />
                  <span className="hidden sm:inline">Send now</span>
                </button>
                <button
                  type="button"
                  onClick={() => onRemove(m.id)}
                  aria-label="Remove"
                  title="Remove"
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border border-red-500/30 bg-red-600/10 hover:bg-red-600/20 focus:outline-none"
                >
                  <MdDelete className="w-4 h-4 text-red-300" />
                  <span className="hidden sm:inline">Remove</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
