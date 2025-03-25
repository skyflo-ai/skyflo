"use client";

import { ChatInterface } from "@/components/ChatInterface";
import Navbar from "@/components/navbar/Navbar";
import { useAuth } from "@/components/auth/AuthProvider";
import { useAuthStore } from "@/store/useAuthStore";

export default function ChatPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { message?: string };
}) {
  const { user } = useAuth();
  const { user: storeUser } = useAuthStore();

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
