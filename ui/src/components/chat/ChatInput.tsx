"use client";

import { MdStop, MdArrowUpward, MdSearch } from "react-icons/md";
import { HiSparkles } from "react-icons/hi2";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { TokenUsage } from "@/types/chat";
import { TokenUsageDisplay } from "./TokenUsageDisplay";

interface ChatInputProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSubmit: (e?: React.FormEvent) => void;
  isStreaming: boolean;
  hasMessages?: boolean;
  onCancel?: () => void;
  topSlot?: ReactNode;
  tokenUsage?: TokenUsage;
}

export function ChatInput({
  inputValue,
  setInputValue,
  handleSubmit,
  isStreaming,
  hasMessages = false,
  onCancel,
  topSlot,
  tokenUsage,
}: ChatInputProps) {
  if (topSlot) {
    return (
      <div className="pb-4 w-full">
        <form onSubmit={handleSubmit} className="relative w-full">
          <div className="w-full relative">
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="relative"
            >
              <div className="relative w-full group">
                <div className="relative rounded-[28px] p-[1.5px] transition-colors duration-200 lg-wrapper">
                  <div className="relative rounded-[28px] overflow-hidden backdrop-blur-2xl backdrop-saturate-150 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),inset_0_-1px_0_rgba(0,0,0,0.35),0_8px_24px_-12px_rgba(0,0,0,0.6)]">
                    <span
                      aria-hidden
                      className="lg-effect rounded-[28px]"
                    ></span>
                    <span aria-hidden className="lg-tint rounded-[28px]"></span>
                    <span
                      aria-hidden
                      className="lg-shine rounded-[28px]"
                    ></span>
                    <span
                      aria-hidden
                      className="lg-vignette rounded-[28px]"
                    ></span>

                    <div className="relative z-10 px-4 py-3 border-b border-white/10">
                      {topSlot}
                    </div>

                    <div className="relative z-10">
                      <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        autoFocus
                        placeholder="Ask Sky to perform any action on your Kubernetes setup"
                        className="w-full bg-transparent text-white text-sm tracking-wide outline-none focus:outline-none focus-visible:outline-none resize-none h-auto min-h-[70px] overflow-hidden transition-[border-color,box-shadow] duration-200 placeholder:text-white/60 p-6 pr-16"
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

                      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
                        <TooltipProvider>
                          {isStreaming ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  onClick={onCancel}
                                  aria-label="Stop response"
                                  className="group inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/10 p-2 backdrop-blur-sm hover:bg-blue-500/20 hover:border-blue-400/60 active:scale-[.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0 transition-[background,border,transform] duration-150"
                                >
                                  <span className="relative flex h-4 w-4 items-center justify-center">
                                    <MdStop className="relative h-4 w-4 text-blue-300" />
                                  </span>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top">
                                <p className="text-white text-xs">
                                  Stop Response
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          ) : (
                            inputValue.trim() && (
                              <button
                                type="submit"
                                aria-label="Send message"
                                title="Send message"
                                className="group inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/10 p-2 backdrop-blur-sm hover:bg-blue-500/15 hover:border-blue-400/60 active:scale-[.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0 transition-[background,border,transform] duration-150"
                              >
                                <span className="relative flex h-5 w-5 items-center justify-center">
                                  <MdArrowUpward className="relative h-5 w-5 text-blue-300" />
                                </span>
                              </button>
                            )
                          )}
                        </TooltipProvider>
                      </div>
                    </div>
                    {tokenUsage && (
                      <div className="relative z-10">
                        <TokenUsageDisplay
                          usage={tokenUsage}
                          visible={isStreaming || hasMessages}
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="pb-4 w-full">
      <form onSubmit={handleSubmit} className="relative w-full">
        <div className="w-full relative">
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="relative"
          >
            <div className="relative w-full group">
              <div className="relative rounded-[28px] p-[1.5px] transition-colors duration-200 lg-wrapper">
                <div className="relative flex flex-col rounded-[28px] backdrop-blur-2xl backdrop-saturate-150 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),inset_0_-1px_0_rgba(0,0,0,0.35),0_8px_24px_-12px_rgba(0,0,0,0.6)]">
                  <span aria-hidden className="lg-effect rounded-[28px]"></span>
                  <span aria-hidden className="lg-tint rounded-[28px]"></span>
                  <span aria-hidden className="lg-shine rounded-[28px]"></span>
                  <span
                    aria-hidden
                    className="lg-vignette rounded-[28px]"
                  ></span>

                  <div className="relative z-10 w-full">
                    <textarea
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      autoFocus
                      placeholder="Ready when you are."
                      className="relative z-10 w-full rounded-[28px] bg-transparent text-white text-sm tracking-wide outline-none focus:outline-none focus-visible:outline-none resize-none h-auto min-h-[60px] overflow-hidden transition-[border-color,box-shadow] duration-200 placeholder:text-white/60 p-6 pr-16"
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

                    <div className="absolute right-4 top-1/2 -translate-y-1/2 z-10 flex items-center gap-2">
                      <TooltipProvider>
                        {isStreaming ? (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <button
                                type="button"
                                onClick={onCancel}
                                aria-label="Stop response"
                                className="group inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/10 p-2 backdrop-blur-sm hover:bg-blue-500/20 hover:border-blue-400/60 active:scale-[.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0 transition-[background,border,transform] duration-150"
                              >
                                <span className="relative flex h-4 w-4 items-center justify-center">
                                  <MdStop className="relative h-4 w-4 text-blue-300" />
                                </span>
                              </button>
                            </TooltipTrigger>
                            <TooltipContent side="top">
                              <p className="text-white text-xs">
                                Stop Response
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        ) : (
                          inputValue.trim() && (
                            <button
                              type="submit"
                              aria-label="Send message"
                              title="Send message"
                              className="group inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/10 p-2 backdrop-blur-sm hover:bg-blue-500/15 hover:border-blue-400/60 active:scale-[.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0 transition-[background,border,transform] duration-150"
                            >
                              <span className="relative flex h-5 w-5 items-center justify-center">
                                <MdArrowUpward className="relative h-5 w-5 text-blue-300" />
                              </span>
                            </button>
                          )
                        )}
                      </TooltipProvider>
                    </div>
                  </div>
                  {tokenUsage && (
                    <div className="relative z-10 w-full">
                      <TokenUsageDisplay
                        usage={tokenUsage}
                        visible={isStreaming || hasMessages}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </form>
    </div>
  );
}
