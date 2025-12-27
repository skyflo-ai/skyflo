"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { TokenUsage } from "@/types/chat";
import {
  MdTimer,
  MdArrowUpward,
  MdArrowDownward,
  MdFunctions,
  MdBolt,
  MdTimelapse,
  MdSpeed,
} from "react-icons/md";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface TokenUsageDisplayProps {
  usage: TokenUsage;
  visible: boolean;
  className?: string;
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + "M";
  if (num >= 1_000) return (num / 1_000).toFixed(1) + "K";
  return num.toLocaleString();
}

function formatNumberWithCommas(num: number): string {
  return Math.round(num).toLocaleString();
}

function formatTime(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function TokenUsageDisplay({
  usage,
  visible,
  className,
}: TokenUsageDisplayProps) {
  const hasTokenUsage = usage.total_tokens > 0;
  const hasTTFT = (usage.ttft ?? 0) > 0;
  const hasTTR = (usage.ttr ?? 0) > 0;
  const hasData = hasTokenUsage || hasTTFT || hasTTR;

  const tps = useMemo(() => {
    if (typeof usage.completion_tokens !== "number") {
      return null;
    }

    let generationTimeMs: number;
    
    if (typeof usage.total_generation_ms === "number" && usage.total_generation_ms > 0) {
      generationTimeMs = usage.total_generation_ms;
    } else if (typeof usage.ttft === "number" && typeof usage.ttr === "number") {
      generationTimeMs = usage.ttr - usage.ttft;
    } else {
      return null;
    }

    if (usage.completion_tokens <= 0 || generationTimeMs <= 0) {
      return null;
    }

    const value = usage.completion_tokens / (generationTimeMs / 1000);
    return Number.isFinite(value) && value > 0 ? value : null;
  }, [usage.completion_tokens, usage.ttft, usage.ttr, usage.total_generation_ms]);

  const formattedTPS = tps?.toFixed(1);
  const hasTPS = formattedTPS !== undefined;


  if (!hasData) {
    return null;
  }

  return (
    <TooltipProvider>
      <motion.div
        initial={false}
        animate={{
          opacity: visible ? 1 : 0,
          y: visible ? 0 : 4,
        }}
        transition={{ duration: 0.2 }}
        className={cn(
          "flex items-center gap-3 px-3 py-4 rounded-b-lg border border-white/10 bg-black/60 backdrop-blur text-[10px] font-medium text-white/70 shadow-lg",
          visible ? "pointer-events-auto" : "pointer-events-none",
          className
        )}
      >
        {hasTTFT && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 hover:text-white/60 transition-colors cursor-default">
                <MdTimer className="w-3.5 h-3.5" />
                <span className="tabular-nums">
                  {formatTime(usage.ttft!)}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p className="text-white text-xs">
                Time to First Token: {formatTime(usage.ttft!)}
              </p>
            </TooltipContent>
          </Tooltip>
        )}

        {hasTPS && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 hover:text-white/60 transition-colors cursor-default">
                <MdSpeed className="w-3.5 h-3.5" />
                <span className="tabular-nums">{formattedTPS} t/s</span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p className="text-white text-xs">Tokens/sec: {formattedTPS}</p>
            </TooltipContent>
          </Tooltip>
        )}

        {hasTTR && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 hover:text-white/60 transition-colors cursor-default">
                <MdTimelapse className="w-3.5 h-3.5" />
                <span className="tabular-nums">{formatTime(usage.ttr!)}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p className="text-white text-xs">
                Time to Respond: {formatTime(usage.ttr!)}
              </p>
            </TooltipContent>
          </Tooltip>
        )}

        {hasTokenUsage && (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 hover:text-white/60 transition-colors cursor-default">
                  <MdArrowUpward className="w-3.5 h-3.5" />
                  <span className="tabular-nums">
                    {formatNumber(usage.prompt_tokens)}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="text-white text-xs">
                  Prompt Tokens:{" "}
                  {formatNumberWithCommas(usage.prompt_tokens)}
                </p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 hover:text-white/60 transition-colors cursor-default">
                  <MdArrowDownward className="w-3.5 h-3.5" />
                  <span className="tabular-nums">
                    {formatNumber(usage.completion_tokens)}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="text-white text-xs">
                  Completion Tokens:{" "}
                  {formatNumberWithCommas(usage.completion_tokens)}
                </p>
              </TooltipContent>
            </Tooltip>

            {usage.cached_tokens > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1.5 text-primary-cyan/70 hover:text-primary-cyan/90 transition-colors cursor-default">
                    <MdBolt className="w-3.5 h-3.5" />
                    <span className="tabular-nums">
                      {formatNumber(usage.cached_tokens)}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top">
                  <p className="text-white text-xs">
                    Cached Tokens:{" "}
                    {formatNumberWithCommas(usage.cached_tokens)}
                  </p>
                </TooltipContent>
              </Tooltip>
            )}

            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 hover:text-white/60 transition-colors cursor-default">
                  <MdFunctions className="w-3.5 h-3.5" />
                  <span className="tabular-nums">
                    {formatNumber(usage.total_tokens)}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="text-white text-xs">
                  Total Tokens:{" "}
                  {formatNumberWithCommas(usage.total_tokens)}
                </p>
              </TooltipContent>
            </Tooltip>
          </>
        )}
      </motion.div>
    </TooltipProvider>
  );
}