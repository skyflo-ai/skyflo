import { useRouter } from "next/navigation";
import ChatHeader from "./ChatHeader";
import ChatSuggestions from "./ChatSuggestions";
import { Suggestion } from "../types";
import ChatInput from "./ChatInput";
import { useState } from "react";
import Loader from "@/components/ui/Loader";
import { createConversation } from "@/lib/api";
import { useWebSocket } from "@/components/WebSocketProvider";
import { queryAgent } from "@/lib/api";

interface WelcomeProps {
  initialSuggestions?: Suggestion[];
}

export default function Welcome({ initialSuggestions }: WelcomeProps) {
  const router = useRouter();
  const { joinConversation } = useWebSocket();

  const [inputValue, setInputValue] = useState("");
  const [isAgentResponding, setIsAgentResponding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initializeConversation = async (message: string) => {
    try {
      setError(null);
      setIsAgentResponding(true);

      // Create a new conversation ID
      const conversationId = crypto.randomUUID();

      // Create the conversation first
      const response = await createConversation(conversationId);

      // Join the WebSocket conversation
      joinConversation(conversationId);

      // Send the initial query
      const chatHistory = [
        {
          role: "user",
          content: message,
          timestamp: Date.now(),
          contextMarker: "latest-query",
          latest: true,
        },
      ];
      const chatHistoryString = JSON.stringify(chatHistory);
      await queryAgent(chatHistoryString, "kubernetes", conversationId);

      // Route to the chat interface with the new conversation ID
      router.push(
        `/chat/${conversationId}?message=${encodeURIComponent(message)}`
      );
    } catch (err) {
      console.error("[Welcome] Failed to create conversation:", err);
      setError("Failed to start conversation. Please try again.");
      setIsAgentResponding(false);
    }
  };

  const handleSuggestionClick = (suggestionText: string) => {
    setInputValue(suggestionText);
    // Focus the textarea after setting the input value
    setTimeout(() => {
      const textArea = document.querySelector("textarea");
      if (textArea) {
        textArea.focus();
      }
    }, 100);
  };

  const handleSubmit = () => {
    if (!inputValue.trim()) return;
    initializeConversation(inputValue);
    setInputValue("");
  };

  return (
    <div className="flex flex-col justify-between h-full w-full">
      <div className="flex-grow overflow-auto px-8 py-4 flex flex-col justify-center items-center">
        {isAgentResponding ? (
          <Loader />
        ) : (
          <>
            {/* Header */}
            <ChatHeader />

            {/* Error Message */}
            {error && (
              <div className="text-red-500 mb-4 text-center">{error}</div>
            )}

            {/* Suggestions */}
            <ChatSuggestions
              suggestions={initialSuggestions}
              onSuggestionClick={handleSuggestionClick}
            />
          </>
        )}
      </div>

      {/* Chat Input - Fixed at bottom */}
      <div className="w-full mt-auto">
        <ChatInput
          inputValue={inputValue}
          setInputValue={setInputValue}
          handleSubmit={handleSubmit}
          handleReloadChat={() => {}}
          isAgentResponding={isAgentResponding}
        />
      </div>
    </div>
  );
}
