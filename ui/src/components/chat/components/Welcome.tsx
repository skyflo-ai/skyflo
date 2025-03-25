import { useRouter } from "next/navigation";
import ChatHeader from "./ChatHeader";
import ChatSuggestions from "./ChatSuggestions";
import { Suggestion } from "../types";
import ChatInput from "./ChatInput";
import { useState } from "react";
import Loader from "@/components/ui/Loader";

interface WelcomeProps {
  initialSuggestions?: Suggestion[];
}

export default function Welcome({ initialSuggestions }: WelcomeProps) {
  const router = useRouter();

  const [inputValue, setInputValue] = useState("");
  const [isAgentResponding, setIsAgentResponding] = useState(false);

  const handleSuggestionClick = (suggestionText: string) => {
    // Create a new conversation ID
    const conversationId = crypto.randomUUID();
    setIsAgentResponding(true);

    // Route to the chat interface with the new conversation ID
    router.push(
      `/chat/${conversationId}?message=${encodeURIComponent(suggestionText)}`
    );
  };

  const handleSubmit = () => {
    // Create a new conversation ID
    const conversationId = crypto.randomUUID();
    setInputValue("");
    setIsAgentResponding(true);

    // Route to the chat interface with the new conversation ID
    router.push(
      `/chat/${conversationId}?message=${encodeURIComponent(inputValue)}`
    );
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
