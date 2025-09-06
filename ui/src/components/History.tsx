"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { format } from "date-fns";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmModal, InputModal } from "@/components/ui/modal";
import Link from "next/link";
import { showSuccess, showError } from "@/components/ui/toast";
import {
  MdChat,
  MdMoreVert,
  MdEdit,
  MdDelete,
  MdSearch,
  MdRefresh,
} from "react-icons/md";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export default function History() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [renameModal, setRenameModal] = useState<{
    isOpen: boolean;
    conversationId: string;
    currentTitle: string;
  }>({ isOpen: false, conversationId: "", currentTitle: "" });
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    conversationId: string;
    title: string;
  }>({ isOpen: false, conversationId: "", title: "" });
  const observerRef = useRef<IntersectionObserver | null>(null);
  const fetchConversationsRef = useRef<() => void>();

  const fetchConversations = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);

    const limit = 25;

    try {
      const url = nextCursor
        ? `/api/conversation?limit=${limit}&cursor=${encodeURIComponent(
            nextCursor
          )}`
        : `/api/conversation?limit=${limit}`;

      const response = await fetch(url);
      const data = await response.json();

      if (
        response.ok &&
        data.status === "success" &&
        Array.isArray(data.data)
      ) {
        setConversations((prev) => {
          const existingIds = new Set(prev.map((conv) => conv.id));
          const newConversations = data.data.filter(
            (conv: Conversation) => !existingIds.has(conv.id)
          );
          return [...prev, ...newConversations];
        });
        setNextCursor(data.pagination?.next_cursor ?? null);
        setHasMore(Boolean(data.pagination?.has_more));
      } else {
        showError("Failed to load your chat history.");
      }
    } catch (error) {
      showError("Failed to load your chat history.");
    } finally {
      setLoading(false);
    }
  }, [hasMore, loading, nextCursor]);

  useEffect(() => {
    fetchConversationsRef.current = fetchConversations;
  }, [fetchConversations]);

  const handleRefresh = useCallback(() => {
    setConversations([]);
    setNextCursor(null);
    setHasMore(true);
    setOpenMenuId(null);
    setTimeout(() => {
      if (fetchConversationsRef.current) {
        fetchConversationsRef.current();
      }
    });
  }, []);

  const handleMenuToggle = (
    conversationId: string,
    event: React.MouseEvent
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(openMenuId === conversationId ? null : conversationId);
  };

  const handleRename = (conversationId: string, event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(null);

    const currentTitle =
      conversations.find((c) => c.id === conversationId)?.title || "";

    setRenameModal({
      isOpen: true,
      conversationId,
      currentTitle,
    });
  };

  const handleRenameSubmit = async (newTitle: string) => {
    const { conversationId, currentTitle } = renameModal;

    if (newTitle && newTitle !== currentTitle) {
      try {
        const response = await fetch(`/api/conversation/${conversationId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ title: newTitle }),
        });

        if (response.ok) {
          setConversations((prev) =>
            prev.map((conv) =>
              conv.id === conversationId ? { ...conv, title: newTitle } : conv
            )
          );
          showSuccess("Chat renamed");
        } else {
          showError("Failed to rename conversation");
        }
      } catch (error) {
        showError("Failed to rename conversation");
      }
    }
  };

  const handleDelete = (conversationId: string, event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(null);

    const conversation = conversations.find((c) => c.id === conversationId);
    if (conversation) {
      setDeleteModal({
        isOpen: true,
        conversationId,
        title: conversation.title,
      });
    }
  };

  const handleDeleteConfirm = async () => {
    const { conversationId } = deleteModal;

    try {
      const response = await fetch(`/api/conversation/${conversationId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setConversations((prev) =>
          prev.filter((conv) => conv.id !== conversationId)
        );
        showSuccess("Chat deleted");
      } else {
        showError("Failed to delete conversation");
      }
    } catch (error) {
      showError("Failed to delete conversation");
    }
  };

  useEffect(() => {
    const handleClickOutside = () => {
      setOpenMenuId(null);
    };

    if (openMenuId) {
      document.addEventListener("click", handleClickOutside);
      return () => {
        document.removeEventListener("click", handleClickOutside);
      };
    }
  }, [openMenuId]);

  useEffect(() => {
    if (conversations.length === 0 && hasMore && !loading) {
      fetchConversations();
    }
  }, []);

  const displayConversations = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    let items = conversations;
    if (query) {
      items = items.filter((c) => c.title.toLowerCase().includes(query));
    }
    return items;
  }, [conversations, searchQuery]);

  useEffect(() => {
    const sentinel = document.getElementById("scroll-sentinel");
    if (!sentinel) return;

    if (observerRef.current) observerRef.current.disconnect();

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const isIntersecting = entries[0].isIntersecting;
        if (
          isIntersecting &&
          !loading &&
          hasMore &&
          fetchConversationsRef.current
        ) {
          fetchConversationsRef.current();
        }
      },
      { threshold: 1.0 }
    );

    observerRef.current.observe(sentinel);

    return () => {
      if (observerRef.current) observerRef.current.disconnect();
    };
  }, [hasMore, loading]);

  return (
    <div className="flex flex-col h-full w-full overflow-auto px-2 py-2">
      {conversations.length > 0 && (
        <div
          className="relative bg-[#0A1525]/50 border border-[#1E2D45] 
                    p-8 rounded-xl border border-[#243147]/60 backdrop-blur-md shadow-lg shadow-blue-900/10 overflow-hidden mb-8"
        >
          <div className="absolute inset-0 bg-blue-600/5 rounded-xl" />
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-transparent rounded-xl" />

          <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center">
            <div className="flex-1">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-400 bg-clip-text text-transparent tracking-tight flex items-center">
                Chat History
              </h1>
            </div>
            <div className="w-full md:w-auto mt-4 md:mt-0 flex items-center gap-2">
              <div className="relative w-full md:w-80">
                <MdSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  aria-label="Search chats"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search chats"
                  className="w-full pl-10 pr-3 p-2 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                />
              </div>
              <button
                onClick={handleRefresh}
                aria-label="Refresh chats"
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-button-primary duration-300 border border-slate-700/60 text-slate-200 hover:border-blue-500/50 group transition-colors"
              >
                <MdRefresh
                  className={`${
                    loading ? "animate-spin" : ""
                  } text-blue-400/70 group-hover:text-blue-400 duration-300`}
                />
                <span className="hidden md:inline group-hover:text-slate-100">
                  Refresh
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="h-full">
        {conversations.length === 0 && loading ? (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-4"
              >
                <Skeleton className="h-6 w-2/3 bg-slate-700/50 mb-2" />
                <Skeleton className="h-4 w-1/3 bg-slate-700/30" />
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex justify-center items-center h-full">
            <div className="text-center py-12 px-4">
              <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 inline-block">
                <MdChat className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-300 mb-2">
                  No chats yet
                </h3>
                <p className="text-slate-400">
                  Start a new chat from the chat page to see your history here.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <>
            {displayConversations.length === 0 ? (
              <div className="text-center py-12 px-4">
                <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 inline-block">
                  <h3 className="text-lg font-semibold text-slate-300 mb-2">
                    No results found
                  </h3>
                  <p className="text-slate-400">Try a different search term.</p>
                </div>
              </div>
            ) : null}
            <div className="grid gap-5 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {displayConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className="relative group transition-all duration-300"
                >
                  <Link href={`/chat/${conversation.id}`} className="block">
                    <div
                      className="bg-blue-500/10 border border-[#1E2D45] 
                   hover:border-blue-500/30 hover:bg-blue-500/15 rounded-lg border p-4 h-full transition-all duration-200 transform hover:-translate-y-0.5"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="text-lg text-slate-200 truncate transition-colors flex-1 pr-2">
                          {conversation.title}
                        </h3>
                        <div className="relative">
                          <button
                            onClick={(e) =>
                              handleMenuToggle(conversation.id, e)
                            }
                            className="p-1 rounded-md hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors opacity-0 group-hover:opacity-100"
                            aria-label="More options"
                            aria-expanded={openMenuId === conversation.id}
                          >
                            <MdMoreVert className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                      <div className="flex flex-col gap-1">
                        <p className="text-xs text-slate-400">
                          {format(
                            new Date(conversation.created_at),
                            "MMM d, yyyy • h:mm a"
                          )}
                        </p>
                      </div>
                    </div>
                  </Link>

                  {openMenuId === conversation.id && (
                    <div className="absolute right-4 top-12 bg-[#1A2332] border border-slate-600/60 rounded-lg shadow-lg shadow-black/20 z-[100] min-w-[150px]">
                      <button
                        onClick={(e) => handleRename(conversation.id, e)}
                        className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700/50 rounded-t-lg transition-colors flex items-center gap-2"
                      >
                        <MdEdit className="w-4 h-4" />
                        Rename
                      </button>
                      <button
                        onClick={(e) => handleDelete(conversation.id, e)}
                        className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 rounded-b-lg transition-colors flex items-center gap-2"
                      >
                        <MdDelete className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        <div id="scroll-sentinel" className="h-8" />
        {conversations.length > 0 && loading && (
          <div className="py-4 text-center text-slate-400">Loading more…</div>
        )}
      </div>

      <InputModal
        isOpen={renameModal.isOpen}
        onClose={() =>
          setRenameModal({
            isOpen: false,
            conversationId: "",
            currentTitle: "",
          })
        }
        onSubmit={handleRenameSubmit}
        title="Rename Chat"
        label="Chat Title"
        placeholder="Enter a new title for this conversation"
        defaultValue={renameModal.currentTitle}
        submitText="Rename"
      />

      <ConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() =>
          setDeleteModal({ isOpen: false, conversationId: "", title: "" })
        }
        onConfirm={handleDeleteConfirm}
        title="Delete Chat"
        message={`Are you sure you want to delete "${deleteModal.title}"?`}
        confirmText="Delete"
        variant="danger"
      />
    </div>
  );
}
