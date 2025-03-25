"use client";

import React, { useEffect, useState } from "react";
import { format } from "date-fns";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { showError } from "@/lib/toast";
import { MdHistory, MdChat } from "react-icons/md";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export default function History() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        setLoading(true);
        const response = await fetch("/api/history");
        const data = await response.json();

        if (
          response.ok &&
          data.status === "success" &&
          Array.isArray(data.data)
        ) {
          setConversations(data.data);
        } else {
          console.error("Error response:", data);
          showError("Failed to load your conversation history.");
        }
      } catch (error) {
        console.error("Error fetching conversations:", error);
        showError("Failed to load your conversation history.");
      } finally {
        setLoading(false);
      }
    };

    fetchConversations();
  }, []);

  return (
    <div className="flex flex-col h-full w-full overflow-auto px-2 py-2">
      {/* Header Section */}
      <div className="relative bg-gradient-to-r from-[#0A1525] via-[#0F182A]/95 to-[#1A2C48]/90 p-8 rounded-xl border border-[#243147]/60 backdrop-blur-md shadow-lg shadow-blue-900/10 overflow-hidden mb-8">
        <div className="absolute inset-0 bg-blue-600/5 rounded-xl" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-transparent rounded-xl" />

        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center">
          <div className="flex-1">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-400 bg-clip-text text-transparent tracking-tight flex items-center">
              Conversation History
            </h1>
            <p className="text-gray-400 mt-2 max-w-2xl">
              View and manage your past conversations with Skyflo.ai
            </p>
          </div>
        </div>

        <div className="absolute bottom-0 right-0 opacity-10 transform translate-x-8 translate-y-4">
          <div className="flex items-end">
            <MdHistory className="text-blue-400 w-32 h-32" />
          </div>
        </div>
      </div>

      <div className="">
        {loading ? (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-[#0F1D2F] rounded-lg border border-slate-700/60 p-4"
              >
                <Skeleton className="h-6 w-2/3 bg-slate-700/50 mb-2" />
                <Skeleton className="h-4 w-1/3 bg-slate-700/30" />
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="bg-[#0F1D2F] rounded-lg border border-slate-700/60 p-8 inline-block">
              <MdChat className="w-12 h-12 text-slate-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-300 mb-2">
                No conversations yet
              </h3>
              <p className="text-slate-400">
                Start a new conversation from the chat page to see your history
                here.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {conversations.map((conversation) => (
              <Link
                href={`/chat/${conversation.id}`}
                key={conversation.id}
                className="group transition-all duration-300"
              >
                <div className="bg-[#0F1D2F] rounded-lg border border-slate-700/60 p-4 h-full hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
                  <h3 className="text-lg font-semibold text-slate-200 mb-2 truncate group-hover:text-blue-400 transition-colors">
                    {conversation.title}
                  </h3>
                  <p className="text-xs text-slate-400">
                    {format(
                      new Date(conversation.created_at),
                      "MMM d, yyyy • h:mm a"
                    )}
                  </p>
                  <div className="mt-4 flex items-center text-sm text-slate-400 group-hover:text-blue-400 transition-colors">
                    <span>View conversation</span>
                    <svg
                      className="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
