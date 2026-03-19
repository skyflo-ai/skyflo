"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import {
  MdSearch,
  MdMoreVert,
  MdEdit,
  MdDelete,
  MdChat,
} from "react-icons/md";
import { useRouter, usePathname } from "next/navigation";
import { ConfirmModal, InputModal } from "@/components/ui/modal";
import { showSuccess, showError } from "@/components/ui/toast";
import { useDebouncedFunction } from "@/lib/debounce";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

type ConversationTitleGeneratedDetail = {
  conversationId: string;
  title: string;
  timestamp?: number;
};

type ConversationCreatedDetail = {
  conversationId: string;
  timestamp?: number;
};

interface ConversationFetchOptions {
  searchTerm?: string;
  nextCursor?: string | null;
  shouldReset?: boolean;
}

type ConversationListCache = {
  conversations: Conversation[];
  nextCursor: string | null;
  hasMore: boolean;
  loaded: boolean;
};

const sidebarConversationCache: ConversationListCache = {
  conversations: [],
  nextCursor: null,
  hasMore: true,
  loaded: false,
};

export function resetSidebarConversationCache(): void {
  sidebarConversationCache.conversations = [];
  sidebarConversationCache.nextCursor = null;
  sidebarConversationCache.hasMore = true;
  sidebarConversationCache.loaded = false;
}

function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);
  const monthAgo = new Date(today);
  monthAgo.setDate(monthAgo.getDate() - 30);

  if (date >= today) return "Today";
  if (date >= yesterday) return "Yesterday";
  if (date >= weekAgo) return "Previous 7 Days";
  if (date >= monthAgo) return "Previous 30 Days";
  return format(date, "MMMM yyyy");
}

function groupConversationsByDate(conversations: Conversation[]) {
  const groups: { label: string; conversations: Conversation[] }[] = [];
  const orderMap: Record<string, number> = {};

  for (const conv of conversations) {
    const group = getDateGroup(conv.updated_at);
    if (!(group in orderMap)) {
      orderMap[group] = groups.length;
      groups.push({ label: group, conversations: [] });
    }
    groups[orderMap[group]].conversations.push(conv);
  }

  return groups;
}

function getConversationDisplayTitle(title: string): string {
  const normalizedTitle = title.trim();
  return normalizedTitle.length > 0 ? normalizedTitle : "Untitled chat";
}

function mergeConversationLists(
  existing: Conversation[],
  incoming: Conversation[],
): Conversation[] {
  const incomingById = new Map(incoming.map((conversation) => [conversation.id, conversation]));
  const mergedExisting = existing.map((conversation) => {
    const serverConversation = incomingById.get(conversation.id);
    if (!serverConversation) {
      return conversation;
    }

    incomingById.delete(conversation.id);
    return { ...conversation, ...serverConversation };
  });

  return [...mergedExisting, ...Array.from(incomingById.values())];
}

interface SidebarHistoryProps {
  searchInputRef: React.RefObject<HTMLInputElement | null>;
}

export default function SidebarHistory({ searchInputRef }: SidebarHistoryProps) {
  const router = useRouter();
  const pathname = usePathname();

  const [conversations, setConversations] = useState<Conversation[]>(
    () => sidebarConversationCache.conversations,
  );
  const [loading, setLoading] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(
    () => sidebarConversationCache.nextCursor,
  );
  const [hasMore, setHasMore] = useState(
    () => sidebarConversationCache.hasMore,
  );
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
  const [typingTitles, setTypingTitles] = useState<Record<string, string>>({});

  const observerRef = useRef<IntersectionObserver | null>(null);
  const fetchConversationsRef = useRef<
    ((ops: ConversationFetchOptions) => Promise<void>) | null
  >(null);
  const activeSearchTermRef = useRef("");
  const typingTimersRef = useRef<Record<string, number>>({});
  const hasMoreRef = useRef(hasMore);
  const loadingRef = useRef(loading);
  const nextCursorRef = useRef(nextCursor);
  const searchQueryRef = useRef(searchQuery);

  const currentChatId = pathname.startsWith("/chat/")
    ? pathname.split("/chat/")[1]
    : null;

  const startTitleTypingEffect = useCallback((conversationId: string, title: string) => {
    const normalizedTitle = title.trim();
    const existingTimer = typingTimersRef.current[conversationId];
    if (existingTimer) {
      window.clearInterval(existingTimer);
      delete typingTimersRef.current[conversationId];
    }

    if (!normalizedTitle) {
      setTypingTitles((prev) => {
        const next = { ...prev };
        delete next[conversationId];
        return next;
      });
      return;
    }

    setTypingTitles((prev) => ({ ...prev, [conversationId]: "" }));
    let index = 0;
    const intervalId = window.setInterval(() => {
      index += 1;
      setTypingTitles((prev) => ({
        ...prev,
        [conversationId]: normalizedTitle.slice(0, index),
      }));
      if (index >= normalizedTitle.length) {
        const timerId = typingTimersRef.current[conversationId];
        if (timerId) {
          window.clearInterval(timerId);
          delete typingTimersRef.current[conversationId];
        }
        setTypingTitles((prev) => {
          const next = { ...prev };
          delete next[conversationId];
          return next;
        });
      }
    }, 60);

    typingTimersRef.current[conversationId] = intervalId;
  }, []);

  const fetchConversations = useCallback(
    async (ops: ConversationFetchOptions) => {
      const { searchTerm = "", nextCursor, shouldReset = false } = ops || {};
      const normalizedSearchTerm = searchTerm.trim();
      const isDefaultHistory = normalizedSearchTerm.length === 0;

      setLoading(true);
      const limit = 25;

      try {
        let url = nextCursor
          ? `/api/conversation?limit=${limit}&cursor=${encodeURIComponent(nextCursor)}`
          : `/api/conversation?limit=${limit}`;

        if (normalizedSearchTerm.length >= 2) {
          url = url.concat(
            `&query=${encodeURIComponent(normalizedSearchTerm)}`,
          );
        }

        const response = await fetch(url);
        const data = await response.json();

        if (
          response.ok &&
          data.status === "success" &&
          Array.isArray(data.data)
        ) {
          if (normalizedSearchTerm !== activeSearchTermRef.current) {
            return;
          }
          setConversations((prev) => {
            if (shouldReset) return data.data;
            return mergeConversationLists(prev, data.data);
          });
          const resolvedNextCursor = data.pagination?.next_cursor ?? null;
          const resolvedHasMore = Boolean(data.pagination?.has_more);
          setNextCursor(resolvedNextCursor);
          setHasMore(resolvedHasMore);

          if (isDefaultHistory) {
            sidebarConversationCache.conversations = shouldReset
              ? data.data
              : mergeConversationLists(
                  sidebarConversationCache.conversations,
                  data.data,
                );
            sidebarConversationCache.nextCursor = resolvedNextCursor;
            sidebarConversationCache.hasMore = resolvedHasMore;
            sidebarConversationCache.loaded = true;
          }
        }
      } catch (error) {
        // Sidebar history fetch is non-critical
        console.error("Failed to fetch sidebar conversation history:", error);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const upsertConversationWithLatestTitle = useCallback(
    (conversationId: string, title: string, timestamp?: number) => {
      const isoTimestamp = new Date(timestamp ?? Date.now()).toISOString();
      const updater = (list: Conversation[]) => {
        const existing = list.find((conv) => conv.id === conversationId);
        if (existing) {
          const updatedConversation: Conversation = {
            ...existing,
            title,
            updated_at: isoTimestamp,
          };
          return [
            updatedConversation,
            ...list.filter((conv) => conv.id !== conversationId),
          ];
        }
        return [
          {
            id: conversationId,
            title,
            created_at: isoTimestamp,
            updated_at: isoTimestamp,
          },
          ...list,
        ];
      };

      sidebarConversationCache.conversations = updater(
        sidebarConversationCache.conversations,
      );

      if (activeSearchTermRef.current.length === 0) {
        setConversations((prev) => updater(prev));
      }
    },
    [],
  );

  const upsertConversationPlaceholder = useCallback(
    (conversationId: string, timestamp?: number) => {
      const isoTimestamp = new Date(timestamp ?? Date.now()).toISOString();
      const updater = (list: Conversation[]) => {
        const existing = list.find((conv) => conv.id === conversationId);
        if (existing) {
          return [
            {
              ...existing,
              updated_at: isoTimestamp,
            },
            ...list.filter((conv) => conv.id !== conversationId),
          ];
        }
        return [
          {
            id: conversationId,
            title: "",
            created_at: isoTimestamp,
            updated_at: isoTimestamp,
          },
          ...list,
        ];
      };

      sidebarConversationCache.conversations = updater(
        sidebarConversationCache.conversations,
      );

      if (activeSearchTermRef.current.length === 0) {
        setConversations((prev) => updater(prev));
      }
    },
    [],
  );

  const handleSearch = useCallback(
    (query: string) => {
      const normalizedQuery = query.trim();

      if (
        normalizedQuery.length === 0 &&
        activeSearchTermRef.current.length === 0 &&
        sidebarConversationCache.loaded
      ) {
        return;
      }

      activeSearchTermRef.current = normalizedQuery;

      if (normalizedQuery.length === 0 && sidebarConversationCache.loaded) {
        setConversations(sidebarConversationCache.conversations);
        setNextCursor(sidebarConversationCache.nextCursor);
        setHasMore(sidebarConversationCache.hasMore);
      } else {
        setConversations([]);
        setNextCursor(null);
        setHasMore(true);
      }

      setOpenMenuId(null);
      fetchConversations({
        searchTerm: normalizedQuery,
        nextCursor: null,
        shouldReset: normalizedQuery.length === 0,
      });
    },
    [fetchConversations],
  );

  const { execute: debouncedSearch } = useDebouncedFunction(handleSearch, 400);

  const handleRename = (conversationId: string, event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(null);
    const currentTitle =
      conversations.find((c) => c.id === conversationId)?.title || "";
    setRenameModal({ isOpen: true, conversationId, currentTitle });
  };

  const handleRenameSubmit = async (formData: FormData) => {
    const { conversationId, currentTitle } = renameModal;
    const newTitle = String(formData.get("title") || "");

    if (newTitle && newTitle !== currentTitle) {
      try {
        const response = await fetch(`/api/conversation/${conversationId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: newTitle }),
        });

        if (response.ok) {
          setConversations((prev) =>
            prev.map((conv) =>
              conv.id === conversationId ? { ...conv, title: newTitle } : conv,
            ),
          );
          sidebarConversationCache.conversations =
            sidebarConversationCache.conversations.map((conv) =>
              conv.id === conversationId ? { ...conv, title: newTitle } : conv,
            );
          showSuccess("Chat renamed");
        } else {
          showError("Failed to rename conversation");
        }
      } catch {
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
        title: getConversationDisplayTitle(conversation.title),
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
          prev.filter((conv) => conv.id !== conversationId),
        );
        sidebarConversationCache.conversations =
          sidebarConversationCache.conversations.filter(
            (conv) => conv.id !== conversationId,
          );
        showSuccess("Chat deleted");
        if (pathname === `/chat/${conversationId}`) {
          router.push("/");
        }
      } else {
        showError("Failed to delete conversation");
      }
    } catch {
      showError("Failed to delete conversation");
    }
  };

  useEffect(() => {
    const handleClickOutside = () => setOpenMenuId(null);
    if (openMenuId) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [openMenuId]);

  useEffect(() => {
    hasMoreRef.current = hasMore;
    loadingRef.current = loading;
    nextCursorRef.current = nextCursor;
    searchQueryRef.current = searchQuery;
  }, [hasMore, loading, nextCursor, searchQuery]);

  useEffect(() => {
    const sentinel = document.getElementById("sidebar-scroll-sentinel");
    if (!sentinel) return;

    if (observerRef.current) observerRef.current.disconnect();

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (
          entries[0].isIntersecting &&
          !loadingRef.current &&
          hasMoreRef.current &&
          fetchConversationsRef.current
        ) {
          const trimmedSearch = searchQueryRef.current.trim();
          const currentSearchTerm =
            trimmedSearch.length < 2 ? "" : trimmedSearch;
          fetchConversationsRef.current({
            nextCursor: nextCursorRef.current,
            searchTerm: currentSearchTerm,
            shouldReset: false,
          });
        }
      },
      { threshold: 1.0 },
    );

    observerRef.current.observe(sentinel);

    return () => {
      if (observerRef.current) observerRef.current.disconnect();
    };
  }, []);

  useEffect(() => {
    const cleanedSearchTerm = searchQuery.trim();
    if (cleanedSearchTerm.length === 0 || cleanedSearchTerm.length >= 2) {
      debouncedSearch(cleanedSearchTerm);
    }
  }, [searchQuery, debouncedSearch]);

  useEffect(() => {
    fetchConversationsRef.current = fetchConversations;
  }, [fetchConversations]);

  useEffect(() => {
    if (sidebarConversationCache.loaded) return;
    fetchConversations({ nextCursor: null, shouldReset: true });
  }, [fetchConversations]);

  useEffect(() => {
    const handleTitleGenerated = (evt: Event) => {
      const event = evt as CustomEvent<ConversationTitleGeneratedDetail>;
      const detail = event?.detail;
      if (!detail?.conversationId || !detail.title) {
        return;
      }
      upsertConversationWithLatestTitle(
        detail.conversationId,
        detail.title,
        detail.timestamp,
      );
      startTitleTypingEffect(detail.conversationId, detail.title);
    };

    window.addEventListener(
      "conversation:title-generated",
      handleTitleGenerated as EventListener,
    );
    return () => {
      window.removeEventListener(
        "conversation:title-generated",
        handleTitleGenerated as EventListener,
      );
    };
  }, [startTitleTypingEffect, upsertConversationWithLatestTitle]);

  useEffect(() => {
    const handleConversationCreated = (evt: Event) => {
      const event = evt as CustomEvent<ConversationCreatedDetail>;
      const detail = event?.detail;
      if (!detail?.conversationId) {
        return;
      }
      upsertConversationPlaceholder(detail.conversationId, detail.timestamp);
    };

    window.addEventListener(
      "conversation:created",
      handleConversationCreated as EventListener,
    );
    return () => {
      window.removeEventListener(
        "conversation:created",
        handleConversationCreated as EventListener,
      );
    };
  }, [upsertConversationPlaceholder]);

  useEffect(() => {
    return () => {
      Object.values(typingTimersRef.current).forEach((timerId) =>
        window.clearInterval(timerId),
      );
      typingTimersRef.current = {};
    };
  }, []);

  const conversationGroups = groupConversationsByDate(conversations);
  const getRenderedTitle = (conversation: Conversation) =>
    Object.prototype.hasOwnProperty.call(typingTitles, conversation.id)
      ? typingTitles[conversation.id]
      : getConversationDisplayTitle(conversation.title);

  return (
    <>
      <div className="px-3 mb-2 shrink-0">
        <div className="relative">
          <MdSearch
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500"
            size={18}
          />
          <input
            ref={searchInputRef}
            type="search"
            aria-label="Search chats"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats"
            className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-zinc-200 placeholder-zinc-600 text-sm outline-none focus:border-white/[0.15] transition-colors duration-200"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto sidebar-scroll px-1.5 pb-2">
        {conversations.length === 0 && loading ? (
          <div className="space-y-1.5 px-1.5 pt-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-9 bg-white/[0.03] rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center pt-16 px-4">
            <MdChat className="w-6 h-6 text-zinc-600 mb-2" />
            <p className="text-sm text-zinc-500 text-center">
              {searchQuery.trim().length > 0
                ? "No results found"
                : "No chats yet"}
            </p>
          </div>
        ) : (
          conversationGroups.map((group) => (
            <div key={group.label} className="mb-2">
              <div className="px-2 pt-4 pb-1.5">
                <span className="text-xs font-medium text-zinc-500">
                  {group.label}
                </span>
              </div>
              {group.conversations.map((conversation) => (
                <div key={conversation.id} className="relative group">
                  <Link
                    href={`/chat/${conversation.id}`}
                    className={`flex items-center w-full px-2.5 py-2 rounded-lg text-left transition-colors duration-150 ${
                      currentChatId === conversation.id
                        ? "bg-dark-active text-white"
                        : "text-zinc-300 hover:bg-dark-hover"
                    }`}
                  >
                    <span className="text-sm truncate flex-1 pr-6">
                      {getRenderedTitle(conversation)}
                    </span>
                  </Link>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setOpenMenuId(
                        openMenuId === conversation.id
                          ? null
                          : conversation.id,
                      );
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-zinc-500 hover:text-zinc-300 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity shrink-0 cursor-pointer"
                    aria-label="More options"
                  >
                    <MdMoreVert size={18} />
                  </button>

                  {openMenuId === conversation.id && (
                    <div className="absolute right-1 top-9 bg-zinc-950/95 backdrop-blur-sm border border-white/[0.08] rounded-lg shadow-2xl z-[100] min-w-[130px]">
                      <button
                        onClick={(e) => handleRename(conversation.id, e)}
                        className="w-full px-3 py-2.5 text-left text-sm text-zinc-300 hover:bg-white/[0.04] rounded-t-lg transition-colors flex items-center gap-2 cursor-pointer"
                      >
                        <MdEdit size={16} />
                        Rename
                      </button>
                      <button
                        onClick={(e) => handleDelete(conversation.id, e)}
                        className="w-full px-3 py-2.5 text-left text-sm text-rose-400 hover:bg-rose-500/5 rounded-b-lg transition-colors flex items-center gap-2 cursor-pointer"
                      >
                        <MdDelete size={16} />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))
        )}

        <div id="sidebar-scroll-sentinel" className="h-4" />
        {conversations.length > 0 && loading && (
          <div className="py-2 text-center text-sm text-zinc-600">
            Loading...
          </div>
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
        submitText="Rename"
      >
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-2">
            Chat Title
          </label>
          <input
            type="text"
            name="title"
            defaultValue={renameModal.currentTitle}
            placeholder="Enter a new title"
            className="w-full p-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-zinc-200 placeholder-zinc-600 outline-none focus:border-white/[0.15] transition-colors duration-200"
            autoFocus
            required
          />
        </div>
      </InputModal>

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
    </>
  );
}
