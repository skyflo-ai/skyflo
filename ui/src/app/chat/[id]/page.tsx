"use client";

import { ChatInterface } from "@/components/ChatInterface";
import Navbar from "@/components/navbar/Navbar";

export default function ChatPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { message?: string };
}) {
  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow">
        <ChatInterface
          conversationId={params.id}
          initialMessage={searchParams.message}
        />
      </div>
    </div>
  );
}
