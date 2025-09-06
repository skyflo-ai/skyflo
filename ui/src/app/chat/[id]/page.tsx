"use client";

import { ChatInterface } from "@/components/chat";
import Navbar from "@/components/navbar/Navbar";

export default function ChatPage({ params }: { params: { id: string } }) {
  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow">
        <ChatInterface conversationId={params.id} />
      </div>
    </div>
  );
}
