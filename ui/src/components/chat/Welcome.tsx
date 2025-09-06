"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import ChatHeader from "./ChatHeader";
import ChatSuggestions from "./ChatSuggestions";
import { ChatInput } from "./ChatInput";
import Loader from "@/components/ui/Loader";

export function Welcome() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initializeConversation = async (message: string) => {
    try {
      setError(null);
      setIsInitializing(true);

      const resp = await fetch("/api/conversation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      const data = await resp.json();
      if (resp.ok && data?.id) {
        sessionStorage.setItem(`initialMessage:${data.id}`, message);
        router.push(`/chat/${data.id}`);
        return;
      }
    } catch (err) {
      setError("Failed to start conversation. Please try again.");
      setIsInitializing(false);
    }
  };

  const handleSuggestionClick = (suggestionText: string) => {
    setInputValue(suggestionText);
    setTimeout(() => {
      const textArea = document.querySelector("textarea");
      if (textArea) {
        textArea.focus();
        textArea.setSelectionRange(
          suggestionText.length,
          suggestionText.length
        );
      }
    }, 100);
  };

  const handleSubmit = () => {
    if (!inputValue.trim()) return;
    initializeConversation(inputValue);
    setInputValue("");
  };

  return (
    <div className="flex flex-col h-full w-full">
      {isInitializing ? (
        <div className="flex-grow flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center space-y-4"
          >
            <Loader />
          </motion.div>
        </div>
      ) : (
        <>
          {error && (
            <div className="flex-shrink-0 px-8 pt-4">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-red-500 text-center p-3 bg-red-500/10 border border-red-500/20 rounded-lg max-w-5xl mx-auto"
              >
                {error}
              </motion.div>
            </div>
          )}

          <div className="flex-grow flex flex-col items-center justify-center px-8">
            <div className="w-full max-w-5xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="mb-8"
              >
                <ChatHeader />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="mb-4"
              >
                <ChatInput
                  inputValue={inputValue}
                  setInputValue={setInputValue}
                  handleSubmit={handleSubmit}
                  isStreaming={isInitializing}
                  hasMessages={false}
                />
              </motion.div>
            </div>
          </div>

          <div className="flex-shrink-0 h-8"></div>
        </>
      )}
    </div>
  );
}
