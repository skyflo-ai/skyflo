import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaChevronDown,
  FaChevronUp,
  FaTerminal,
  FaCopy,
  FaCheckCircle,
} from "react-icons/fa";
import { HiOutlineTerminal } from "react-icons/hi";

interface TerminalOutputProps {
  command: string;
  output: string;
  tool: string;
  action: string;
  stepId: string;
  status: "pending" | "executing" | "completed" | "failed";
  parameters?: Record<string, any>;
}

const TerminalOutput: React.FC<TerminalOutputProps> = ({
  command,
  output,
  tool,
  action,
  stepId,
  status,
  parameters = {},
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isCopied, setIsCopied] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const statusColor = () => {
    switch (status) {
      case "completed":
        return "text-green-500";
      case "failed":
        return "text-red-500";
      case "executing":
        return "text-blue-500";
      default:
        return "text-gray-500";
    }
  };

  const formatParameters = () => {
    try {
      return Object.entries(parameters)
        .map(([key, value]) => {
          if (typeof value === "object") {
            return `--${key}='${JSON.stringify(value)}'`;
          } else {
            return `--${key}='${value}'`;
          }
        })
        .join(" ");
    } catch (e) {
      return JSON.stringify(parameters);
    }
  };

  // Format the command nicely for display
  const displayCommand = `$ ${tool} ${action} ${formatParameters()}`;

  return (
    <div className="border border-gray-700 rounded-md overflow-hidden bg-gray-900 my-3 shadow-lg">
      <div
        className="flex items-center justify-between p-2 bg-gray-800 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <HiOutlineTerminal className={`${statusColor()} text-lg`} />
          <span className="font-mono text-sm text-gray-300">
            <span className={statusColor()}>
              {status === "completed"
                ? "✓ "
                : status === "failed"
                ? "✗ "
                : status === "executing"
                ? "⟳ "
                : "○ "}
            </span>
            <span className="font-semibold">{tool}</span> {action}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              copyToClipboard(displayCommand);
            }}
            className="text-gray-400 hover:text-blue-400 focus:outline-none"
            title="Copy command"
          >
            {isCopied ? (
              <FaCheckCircle className="text-green-500" />
            ) : (
              <FaCopy />
            )}
          </button>
          {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="p-2 bg-gray-900 border-t border-gray-700">
              <div className="bg-gray-950 p-2 rounded font-mono text-sm text-gray-300 overflow-x-auto">
                {displayCommand}
              </div>
            </div>

            {output && (
              <div className="p-2 bg-gray-900">
                <pre className="bg-black p-3 rounded font-mono text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {output}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default TerminalOutput;
