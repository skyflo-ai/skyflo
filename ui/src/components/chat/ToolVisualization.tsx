"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MdKeyboardArrowDown,
  MdKeyboardArrowRight,
  MdCheck,
  MdError,
  MdHourglassEmpty,
  MdSync,
  MdAccessTime,
  MdBlock,
  MdVerifiedUser,
  MdThumbUp,
  MdThumbDown,
} from "react-icons/md";
import { cn } from "@/lib/utils";
import { ToolExecution } from "../../types/chat";
import { approveToolCall, denyToolCall } from "@/lib/approvals";

interface ToolVisualizationProps {
  toolExecution: ToolExecution;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onApprovalAction?: (
    callId: string,
    approve: boolean,
    reason?: string
  ) => void;
  disableActions?: boolean;
}

const expandVariants = {
  collapsed: { height: 0, opacity: 0, overflow: "hidden" },
  expanded: {
    height: "auto",
    opacity: 1,
    transition: {
      height: { duration: 0.3 },
      opacity: { duration: 0.2, delay: 0.1 },
    },
  },
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "executing":
      return (
        <MdSync
          className="w-4 h-4"
          style={{ animation: "spin 1s linear infinite reverse" }}
        />
      );
    case "completed":
      return <MdCheck className="w-4 h-4" />;
    case "error":
      return <MdError className="w-4 h-4" />;
    case "awaiting_approval":
      return <MdAccessTime className="w-4 h-4 animate-pulse" />;
    case "approved":
      return <MdVerifiedUser className="w-4 h-4" />;
    case "denied":
      return <MdBlock className="w-4 h-4" />;
    default:
      return <MdHourglassEmpty className="w-4 h-4" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "executing":
      return "border-blue-600/40 bg-gradient-to-r from-blue-600/15 to-blue-600/5";
    case "completed":
      return "border-emerald-600/40 bg-gradient-to-r from-emerald-500/15 to-emerald-500/5";
    case "error":
      return "border-rose-600/40 bg-gradient-to-r from-rose-500/15 to-rose-500/5";
    case "awaiting_approval":
      return "border-blue-600/40 bg-gradient-to-r from-blue-600/15 to-blue-600/5";
    case "approved":
      return "border-green-600/40 bg-gradient-to-r from-green-500/15 to-green-500/5";
    case "denied":
      return "border-slate-600/40 bg-gradient-to-r from-slate-500/15 to-slate-500/5";
    default:
      return "border-slate-700/40 bg-gradient-to-r from-slate-800/70 to-slate-900/70";
  }
};

const getTextColor = (status: string) => {
  switch (status) {
    case "executing":
      return "text-blue-400";
    case "completed":
      return "text-emerald-400";
    case "error":
      return "text-rose-400";
    case "awaiting_approval":
      return "text-blue-400";
    case "approved":
      return "text-green-400";
    case "denied":
      return "text-slate-400";
    default:
      return "text-slate-400";
  }
};

export function ToolVisualization({
  toolExecution,
  isExpanded = false,
  onToggleExpand,
  onApprovalAction,
  disableActions = false,
}: ToolVisualizationProps) {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isDenying, setIsDenying] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // Auto-collapse when status changes away from awaiting_approval
  useEffect(() => {
    if (toolExecution.status !== "awaiting_approval") {
      setInternalExpanded(false);
    }
  }, [toolExecution.status]);

  const expanded = disableActions
    ? false
    : onToggleExpand
    ? isExpanded || toolExecution.status === "awaiting_approval"
    : internalExpanded || toolExecution.status === "awaiting_approval";
  const toggleExpanded = disableActions
    ? undefined
    : onToggleExpand || (() => setInternalExpanded(!internalExpanded));

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatArgs = (args: Record<string, any>) => {
    return JSON.stringify(args, null, 2);
  };

  const handleApprove = async (reason?: string) => {
    if (isApproving || isDenying || disableActions) return;

    setIsApproving(true);
    setApprovalError(null);

    try {
      if (onApprovalAction) {
        await onApprovalAction(toolExecution.call_id, true, reason);
      } else {
        await approveToolCall(toolExecution.call_id, reason);
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to approve tool";
      setApprovalError(errorMessage);
    } finally {
      setIsApproving(false);
    }
  };

  const handleDeny = async (reason?: string) => {
    if (isApproving || isDenying || disableActions) return;

    setIsDenying(true);
    setApprovalError(null);

    try {
      if (onApprovalAction) {
        await onApprovalAction(toolExecution.call_id, false, reason);
      } else {
        await denyToolCall(toolExecution.call_id, reason);
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to deny tool";
      setApprovalError(errorMessage);
    } finally {
      setIsDenying(false);
    }
  };

  const getResultText = (result?: Array<{ type: string; text?: string }>) => {
    if (!result || result.length === 0) return "No result";

    return result
      .map((item) => {
        if (item.type === "text" && item.text) {
          try {
            const parsed = JSON.parse(item.text);
            if (parsed.content && Array.isArray(parsed.content)) {
              return parsed.content
                .map((content: any) => content.text || content)
                .join("\n");
            }
            return JSON.stringify(parsed, null, 2);
          } catch {
            return item.text;
          }
        }
        return JSON.stringify(item, null, 2);
      })
      .join("\n");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="my-2 max-w-2xl"
    >
      <motion.div
        className={cn(
          "border rounded-lg transition-all duration-300 overflow-hidden",
          getStatusColor(toolExecution.status)
        )}
        whileHover={{
          boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        }}
      >
        <motion.div
          className={cn(
            "p-3",
            !disableActions && "cursor-pointer",
            (toolExecution.status === "executing" ||
              toolExecution.status === "awaiting_approval") &&
              "animate-pulse"
          )}
          onClick={toggleExpanded}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center">
              <motion.div
                className={cn("mr-3", getTextColor(toolExecution.status))}
                animate={
                  toolExecution.status === "executing" ||
                  toolExecution.status === "awaiting_approval"
                    ? {
                        scale: [1, 1.1, 1],
                        transition: { repeat: Infinity, duration: 1.5 },
                      }
                    : {}
                }
              >
                {getStatusIcon(toolExecution.status)}
              </motion.div>
              <div>
                <div className="text-sm font-medium text-slate-100">
                  {toolExecution.title}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {toolExecution.status === "executing"
                    ? "Executing..."
                    : toolExecution.status === "completed"
                    ? "Completed"
                    : toolExecution.status === "error"
                    ? "Error"
                    : toolExecution.status === "pending"
                    ? "Pending"
                    : toolExecution.status === "awaiting_approval"
                    ? "Awaiting approval"
                    : toolExecution.status === "approved"
                    ? "Approved"
                    : toolExecution.status === "denied"
                    ? "Denied"
                    : "Unknown"}
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-500">
                {formatTimestamp(toolExecution.timestamp)}
              </span>
              {expanded ? (
                <MdKeyboardArrowDown
                  className={getTextColor(toolExecution.status)}
                />
              ) : (
                <MdKeyboardArrowRight
                  className={getTextColor(toolExecution.status)}
                />
              )}
            </div>
          </div>
        </motion.div>
        {toolExecution.status === "awaiting_approval" && !disableActions && (
          <div className="px-4 py-3 text-xs text-slate-300">
            <div className="flex items-center justify-left space-x-2">
              Review the tool arguments below before making your decision
            </div>
          </div>
        )}

        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              variants={expandVariants}
              className="bg-dark border-t border-slate-700/50"
            >
              <div className="p-4 space-y-3">
                <div>
                  <div className="text-sm text-slate-400 mb-2">Arguments:</div>
                  <pre className="text-xs text-sky-300 font-mono bg-blue-500/5 p-3 rounded-md border border-slate-700/60 whitespace-pre-wrap break-words break-all max-w-full overflow-x-hidden">
                    {formatArgs(toolExecution.args)}
                  </pre>
                </div>

                {toolExecution.status === "completed" &&
                  toolExecution.result && (
                    <div>
                      <div className="text-sm text-slate-400 mb-2">Result:</div>
                      <pre className="text-xs text-sky-300 font-mono bg-blue-500/5 p-3 rounded-md border border-emerald-600/30 whitespace-pre-wrap break-words break-all max-w-full overflow-x-hidden">
                        {getResultText(toolExecution.result)}
                      </pre>
                    </div>
                  )}

                {toolExecution.status === "error" && toolExecution.error && (
                  <div>
                    <div className="text-sm text-slate-400 mb-2">Error:</div>
                    <pre className="text-xs text-rose-300 font-mono bg-blue-500/5 p-3 rounded-md border border-rose-600/30 whitespace-pre-wrap break-words break-all max-w-full overflow-x-hidden">
                      {toolExecution.error}
                    </pre>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {toolExecution.status === "awaiting_approval" && !disableActions && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="border-t border-blue-600/30 p-4"
          >
            <div className="flex flex-col space-y-4">
              <div className="flex flex-col sm:flex-row gap-3 justify-center items-stretch sm:items-center">
                <motion.button
                  onClick={() => handleApprove()}
                  disabled={isApproving || isDenying || disableActions}
                  className={cn(
                    "flex items-center justify-center space-x-2 px-6 py-2.5 rounded-lg font-medium text-sm transition-[border-color,background-color,transform] duration-200",
                    "bg-green-600/20 border border-green-600/40",
                    "hover:bg-green-600/30 hover:border-green-500/60",
                    "outline-none focus:outline-none focus-visible:outline-none",
                    "active:bg-green-600/25 active:scale-95",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
                    isApproving && "animate-pulse bg-green-600/25",
                    "min-w-[140px] flex-1 sm:flex-none"
                  )}
                  whileTap={{ scale: isApproving || isDenying ? 1 : 0.95 }}
                >
                  {isApproving ? (
                    <MdHourglassEmpty className="w-4 h-4 animate-spin" />
                  ) : (
                    <MdThumbUp className="w-4 h-4 text-green-300" />
                  )}
                  <span>{isApproving ? "Approving..." : "Approve"}</span>
                </motion.button>

                <motion.button
                  onClick={() => handleDeny("User rejected the tool execution")}
                  disabled={isApproving || isDenying || disableActions}
                  className={cn(
                    "flex items-center justify-center space-x-2 px-6 py-2.5 rounded-lg font-medium text-sm transition-[border-color,background-color,transform] duration-100",
                    "bg-red-600/20 border border-red-600/40",
                    "hover:bg-red-600/30 hover:border-red-500/60",
                    "outline-none focus:outline-none focus-visible:outline-none",
                    "active:bg-red-600/25 active:scale-95",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
                    isDenying && "animate-pulse bg-red-600/25",
                    "min-w-[140px] flex-1 sm:flex-none"
                  )}
                  whileTap={{ scale: isApproving || isDenying ? 1 : 0.95 }}
                >
                  {isDenying ? (
                    <MdHourglassEmpty className="w-4 h-4 animate-spin" />
                  ) : (
                    <MdThumbDown className="w-4 h-4 text-red-300" />
                  )}
                  <span>{isDenying ? "Denying..." : "Deny"}</span>
                </motion.button>
              </div>

              <AnimatePresence>
                {approvalError && (
                  <motion.div
                    initial={{ opacity: 0, height: 0, marginTop: 0 }}
                    animate={{ opacity: 1, height: "auto", marginTop: 12 }}
                    exit={{ opacity: 0, height: 0, marginTop: 0 }}
                    transition={{ duration: 0.2 }}
                    className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-xs"
                  >
                    <div className="flex items-center space-x-2">
                      <MdError className="w-4 h-4 flex-shrink-0" />
                      <span>{approvalError}</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}
