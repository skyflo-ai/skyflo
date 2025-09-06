"use client";

import { MdStop, MdArrowUpward } from "react-icons/md";
import { motion } from "framer-motion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

interface ChatInputProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSubmit: (e?: React.FormEvent) => void;
  isStreaming: boolean;
  hasMessages?: boolean;
  onCancel?: () => void;
}

export function ChatInput({
  inputValue,
  setInputValue,
  handleSubmit,
  isStreaming,
  hasMessages = false,
  onCancel,
}: ChatInputProps) {
  return (
    <div className="pb-4 w-full">
      <form onSubmit={handleSubmit} className="relative w-full">
        <div className="w-full relative">
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="relative flex items-center"
          >
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              autoFocus
              placeholder="Ask Sky to perform any action on your Kubernetes setup"
              className="w-full rounded-3xl p-6 pr-16 bg-[#1b1c21] text-white text-sm tracking-wide outline-none focus:outline-none focus-visible:outline-none resize-none h-auto min-h-[70px] overflow-hidden transition-[border-color,box-shadow] duration-200 placeholder:text-[#8693a3] shadow-[0px_-3px_2px_0px_rgba(0,_0,_0,_0.1)]"
              rows={1}
              onInput={(e: React.FormEvent<HTMLTextAreaElement>) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = `${target.scrollHeight}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />

            <div className="absolute right-4 flex items-center gap-2">
              <TooltipProvider>
                {isStreaming ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={onCancel}
                        aria-label="Stop response"
                        className="group inline-flex items-center gap-2 rounded-full
                       border border-blue-400/40 bg-blue-500/10 p-2
                       backdrop-blur-sm
                       hover:bg-blue-500/20 hover:border-blue-400/60
                       active:scale-[.98]
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0
                       transition-[background,border,transform] duration-150
                       "
                      >
                        <span className="relative flex h-4 w-4 items-center justify-center">
                          <MdStop className="relative h-4 w-4 text-blue-300" />
                        </span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top">
                      <p className="text-white text-xs">Stop Response</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  inputValue.trim() && (
                    <button
                      type="submit"
                      aria-label="Send message"
                      title="Send message"
                      className="group inline-flex items-center gap-2 rounded-full
                       border border-blue-400/40 bg-blue-500/10 p-2
                       backdrop-blur-sm
                       hover:bg-blue-500/15 hover:border-blue-400/60
                       active:scale-[.98]
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0
                       transition-[background,border,transform] duration-150
                       "
                    >
                      <span className="relative flex h-5 w-5 items-center justify-center">
                        <MdArrowUpward className="relative h-5 w-5 text-blue-300" />
                      </span>
                    </button>
                  )
                )}
              </TooltipProvider>
            </div>
          </motion.div>
        </div>
      </form>
    </div>
  );
}
