import { useEffect, useRef } from "react";
import { WorkflowMetadata } from "../types";
import { WorkflowVisualizer } from "./WorkflowVisualizer";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";

interface ChatMessagesProps {
  userMessages: any[];
  messageWorkflows: Record<number, WorkflowMetadata>;
  loadingStatusMessage?: string;
  currentProgress: number;
  currentPhase: string;
  isResponseGenerating?: boolean;
  finalResponse?: string;
  onApproveStep?: (stepId: string) => void;
  onRejectStep?: (stepId: string) => void;
}

const messageVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: index * 0.05,
      type: "spring",
      stiffness: 100,
      damping: 20,
    },
  }),
};

export default function ChatMessages({
  userMessages,
  messageWorkflows,
  loadingStatusMessage,
  currentProgress,
  currentPhase,
  isResponseGenerating = false,
  finalResponse,
  onApproveStep,
  onRejectStep,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [userMessages, loadingStatusMessage]);

  return (
    <div className="space-y-4 py-4">
      <AnimatePresence>
        {userMessages.map((message, index) => (
          <motion.div
            key={index}
            initial="hidden"
            animate="visible"
            custom={index}
            variants={messageVariants}
            className="space-y-8"
          >
            {/* Message with User Avatar Outside for User Messages */}
            <div
              className={cn(
                "flex items-start",
                message.from === "user" ? "flex-row-reverse" : ""
              )}
            >
              {/* Avatar for User - Inside the flex container but outside message */}
              {message.from === "user" && (
                <div className="flex-shrink-0 mt-1 mr-2">
                  <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center border border-blue-500/30">
                    <span className="text-blue-400 text-xs font-mediu">
                      You
                    </span>
                  </div>
                </div>
              )}

              {/* Message content */}
              <div
                className={cn(
                  "p-4 rounded-lg max-w-[80%]",
                  message.from === "user"
                    ? "bg-blue-500/10 border border-blue-500/20 mr-2"
                    : message.from === "system"
                    ? "bg-orange-500/10 border border-orange-500/20"
                    : "bg-gradient-to-br from-[#0F172A] to-[#162A3F] border border-[#1E293B]"
                )}
              >
                <div className={cn("prose prose-invert max-w-none")}>
                  {typeof message.message === "string" ? (
                    <ReactMarkdown className="text-base leading-relaxed">
                      {message.message}
                    </ReactMarkdown>
                  ) : (
                    <pre className="text-sm bg-slate-800/50 p-2 rounded-md border border-slate-700 overflow-x-auto max-w-full break-all whitespace-pre-wrap">
                      {JSON.stringify(message.message, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            </div>

            {/* Workflow Visualizer */}
            {message.from === "user" && messageWorkflows[index] && (
              <AnimatePresence>
                <div
                  className={cn(
                    "flex items-start",
                    message.from === "user" ? "" : ""
                  )}
                >
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.5 }}
                    className="mt-4 w-full"
                  >
                    <WorkflowVisualizer
                      currentPlan={messageWorkflows[index].currentPlan}
                      executionSteps={messageWorkflows[index].executionSteps}
                      validationResults={
                        messageWorkflows[index].validationResults
                      }
                      currentPhase={messageWorkflows[index].phase}
                      currentAgentState={messageWorkflows[index].agentState}
                      loadingStatusMessage={loadingStatusMessage}
                      terminalOutputs={messageWorkflows[index].terminalOutputs}
                      finalResponse={finalResponse}
                      onApprove={onApproveStep}
                      onReject={onRejectStep}
                    />
                  </motion.div>
                </div>
              </AnimatePresence>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Loading Status */}
      <AnimatePresence>
        {(loadingStatusMessage || isResponseGenerating) && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="py-4 flex flex-col items-center justify-center"
          >
            {/* Simple, elegant loading animation */}
            <div className="relative w-24 h-6 flex items-center justify-center">
              {/* Simple loading bars */}
              <div className="absolute flex items-center space-x-1.5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <motion.div
                    key={`bar-${i}`}
                    className={cn(
                      "w-1 rounded-full",
                      isResponseGenerating ? "bg-emerald-500" : "bg-blue-500"
                    )}
                    animate={{
                      height: [
                        4 + Math.random() * 3,
                        12 + Math.random() * 8,
                        6 + Math.random() * 4,
                        14 + Math.random() * 6,
                        3 + Math.random() * 3,
                      ],
                      opacity: [0.4, 0.8, 0.6, 0.9, 0.5],
                    }}
                    transition={{
                      duration: 1.5 + Math.random() * 1.0,
                      repeat: Infinity,
                      delay: i * 0.15 + Math.random() * 0.3,
                      ease: "easeInOut",
                      times: [0, 0.2, 0.5, 0.8, 1],
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Status message below animation */}
            <div
              className={cn(
                "mt-3 text-sm font-medium",
                isResponseGenerating ? "text-emerald-200" : "text-blue-200"
              )}
            >
              {isResponseGenerating
                ? "Generating final response..."
                : loadingStatusMessage}
            </div>

            {/* Improved progress bar */}
            {currentProgress > 0 && (
              <div className="mt-2.5 w-48 h-1 bg-[#1A2B44]/70 rounded-full overflow-hidden">
                <motion.div
                  className={cn(
                    "h-full shadow-[0_0_4px_rgba(59,130,246,0.6)]",
                    isResponseGenerating ? "bg-emerald-500" : "bg-blue-500"
                  )}
                  style={{ width: `${currentProgress * 100}%` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${currentProgress * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={messagesEndRef} />
    </div>
  );
}
