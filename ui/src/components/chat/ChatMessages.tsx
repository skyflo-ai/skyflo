"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { ChatMessage } from "../../types/chat";
import { ToolVisualization } from "./ToolVisualization";
import { markdownComponents } from "../ui/markdown-components";

interface ChatMessagesProps {
  messages: ChatMessage[];
  currentMessage?: ChatMessage | null;
  isStreaming: boolean;
  waitingForFirstUpdate: boolean;
  autoScroll?: boolean;
  onApprovalAction?: (
    callId: string,
    approve: boolean,
    reason?: string
  ) => void;
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

export function ChatMessages({
  messages,
  currentMessage,
  isStreaming,
  waitingForFirstUpdate,
  autoScroll = true,
  onApprovalAction,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (autoScroll) {
      scrollToBottom();
    }
  }, [messages, currentMessage, autoScroll]);

  const renderAssistantSegments = (message: ChatMessage) => {
    const segments = message.segments || [];

    return (
      <div className="space-y-2 px-4">
        {segments.map((seg) => {
          if (seg.kind === "text") {
            return (
              <div key={seg.id} className={cn("prose prose-invert max-w-none")}>
                <ReactMarkdown
                  className="text-base leading-relaxed"
                  components={markdownComponents}
                >
                  {seg.text}
                </ReactMarkdown>
              </div>
            );
          }
          return (
            <motion.div
              key={seg.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <ToolVisualization
                toolExecution={seg.toolExecution}
                isExpanded={
                  seg.toolExecution.status === "executing" ||
                  seg.toolExecution.status === "awaiting_approval"
                }
                onApprovalAction={onApprovalAction}
              />
            </motion.div>
          );
        })}
      </div>
    );
  };

  const allMessages = currentMessage ? [...messages, currentMessage] : messages;

  return (
    <div className="space-y-8 py-4">
      <AnimatePresence>
        {allMessages.map((message, index) => (
          <motion.div
            key={message.id}
            initial="hidden"
            animate="visible"
            custom={index}
            variants={messageVariants}
            className="space-y-4"
          >
            <div
              className={cn(
                "flex items-start",
                message.type === "user" ? "flex-row-reverse" : ""
              )}
            >
              <div
                className={cn(
                  message.type === "user"
                    ? "p-4 rounded-lg max-w-[80%]"
                    : "w-[80%]",
                  message.type === "user"
                    ? "bg-blue-500/10 border border-blue-500/20"
                    : ""
                )}
              >
                {message.type === "user" ? (
                  <div className={cn("prose prose-invert max-w-none")}>
                    {message.content}
                  </div>
                ) : (
                  renderAssistantSegments(message)
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {waitingForFirstUpdate && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="py-4 flex flex-col items-center justify-center"
        >
          <div className="relative w-24 h-6 flex items-center justify-center">
            <div className="absolute flex items-center space-x-1.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <motion.div
                  key={`bar-${i}`}
                  className="w-1 rounded-full bg-sky-500"
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
        </motion.div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
