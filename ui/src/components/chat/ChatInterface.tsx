"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { ChatService } from "@/lib/services/sseService";
import { ToolExecution, ChatMessage } from "@/types/chat";
import {
  ChatMessage as ChatMessageType,
  ToolExecution as ToolExecutionType,
  MessageSegment,
} from "../../types/chat";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { stopConversation } from "@/lib/approvals";

interface ChatInterfaceProps {
  conversationId: string;
}

export function ChatInterface({ conversationId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [currentMessage, setCurrentMessage] = useState<ChatMessageType | null>(
    null
  );
  const [inputValue, setInputValue] = useState("");
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [waitingForFirstUpdate, setWaitingForFirstUpdate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isStreaming) {
      setWaitingForFirstUpdate(false);
      return;
    }

    const getLastSegment = () => {
      if (currentMessage?.segments?.length) {
        return currentMessage.segments[currentMessage.segments.length - 1];
      }

      const lastMessage = messages[messages.length - 1];
      if (
        lastMessage?.type === "assistant" &&
        (lastMessage as any).segments?.length
      ) {
        const segments = (lastMessage as any).segments;
        return segments[segments.length - 1];
      }

      return null;
    };

    const lastSegment = getLastSegment();

    if (
      lastSegment?.kind === "text" ||
      (lastSegment?.kind === "tool" &&
        lastSegment.toolExecution.status === "executing")
    ) {
      setWaitingForFirstUpdate(false);
      return;
    }

    if (
      lastSegment?.kind === "tool" &&
      lastSegment.toolExecution.status === "completed"
    ) {
      setWaitingForFirstUpdate(true);
      return;
    }

    const lastMsg = messages[messages.length - 1];
    if (lastMsg?.type === "user") {
      setWaitingForFirstUpdate(true);
    }
  }, [isStreaming, currentMessage?.segments, messages]);

  const chatServiceRef = useRef<ChatService | null>(null);
  const hasFinalizedRef = useRef(false);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const lastScrollTopRef = useRef(0);

  const convertToolExecution = (
    execution: ToolExecution
  ): ToolExecutionType => ({
    call_id: execution.call_id,
    tool: execution.tool,
    title: execution.title,
    args: execution.args,
    status: execution.status,
    result: execution.result,
    timestamp: execution.timestamp,
    error: execution.error,
  });

  const updateMessageWithTool = (execution: ToolExecution) => {
    const toolExecution = convertToolExecution(execution);
    setCurrentMessage((prev) => {
      if (!prev) return prev;

      const prevSegments = prev.segments || [];
      const segIndex = prevSegments.findIndex(
        (s) => s.kind === "tool" && s.id === execution.call_id
      );
      const updatedSegments: MessageSegment[] =
        segIndex >= 0
          ? prevSegments.map((s, i) =>
              s.kind === "tool" && i === segIndex ? { ...s, toolExecution } : s
            )
          : [
              ...prevSegments,
              {
                kind: "tool",
                id: toolExecution.call_id,
                toolExecution,
                timestamp: Date.now(),
              },
            ];

      return {
        ...prev,
        segments: updatedSegments,
      };
    });

    setMessages((prev) => {
      const updated = [...prev];
      for (let idx = updated.length - 1; idx >= 0; idx--) {
        const msg = updated[idx];
        if (msg.type === "assistant" && Array.isArray(msg.segments)) {
          const segIndex = msg.segments.findIndex(
            (s) => s.kind === "tool" && s.id === execution.call_id
          );
          if (segIndex >= 0) {
            const newSegments = msg.segments.map((s, i) =>
              s.kind === "tool" && i === segIndex ? { ...s, toolExecution } : s
            );
            updated[idx] = { ...msg, segments: newSegments } as any;
            break;
          }
        }
      }
      return updated;
    });
  };

  const updateExistingMessageWithTool = (execution: ToolExecution) => {
    const toolExecution = convertToolExecution(execution);
    setCurrentMessage((prev) => {
      if (!prev) return prev;

      const updatedSegments: MessageSegment[] = (prev.segments || []).map((s) =>
        s.kind === "tool" && s.id === execution.call_id
          ? { ...s, toolExecution }
          : s
      );

      return {
        ...prev,
        segments: updatedSegments,
      };
    });
    setMessages((prev) => {
      const updated = [...prev];
      for (let idx = updated.length - 1; idx >= 0; idx--) {
        const msg = updated[idx];
        if (msg.type === "assistant" && Array.isArray((msg as any).segments)) {
          const segIndex = (msg as any).segments.findIndex(
            (s: any) => s.kind === "tool" && s.id === execution.call_id
          );
          if (segIndex >= 0) {
            const newSegments = (msg as any).segments.map((s: any, i: number) =>
              s.kind === "tool" && i === segIndex ? { ...s, toolExecution } : s
            );
            updated[idx] = { ...(msg as any), segments: newSegments } as any;
            break;
          }
        }
      }
      return updated;
    });
  };

  const addPendingTools = (executions: ToolExecution[]) => {
    if (!executions || executions.length === 0) return;
    setWaitingForFirstUpdate(false);
    setCurrentMessage((prev) => {
      if (!prev) {
        const seededSegments: MessageSegment[] = executions.map((e) => ({
          kind: "tool",
          id: e.call_id,
          toolExecution: convertToolExecution(e),
          timestamp: Date.now(),
        }));
        return {
          id: crypto.randomUUID(),
          type: "assistant",
          content: "",
          timestamp: Date.now(),
          isStreaming: true,
          segments: seededSegments,
        } as ChatMessageType;
      }

      const priorSegments = Array.isArray(prev.segments)
        ? [...prev.segments]
        : [];
      const existingToolIds = new Set(
        priorSegments
          .filter((s: any) => s.kind === "tool")
          .map((s: any) => s.id)
      );
      const updatedSegments: MessageSegment[] = priorSegments.map((s: any) => {
        if (s.kind !== "tool") return s;
        const match = executions.find((e) => e.call_id === s.id);
        return match ? { ...s, toolExecution: convertToolExecution(match) } : s;
      });

      for (const e of executions) {
        if (!existingToolIds.has(e.call_id)) {
          updatedSegments.push({
            kind: "tool",
            id: e.call_id,
            toolExecution: convertToolExecution(e),
            timestamp: Date.now(),
          } as any);
          existingToolIds.add(e.call_id);
        }
      }

      return { ...prev, segments: updatedSegments } as any;
    });
  };

  useEffect(() => {
    chatServiceRef.current = new ChatService({
      onToolExecuting: updateMessageWithTool,
      onToolResult: updateExistingMessageWithTool,
      onToolsPending: addPendingTools,
      onToolAwaitingApproval: updateMessageWithTool,
      onToolApproved: updateExistingMessageWithTool,
      onToolDenied: updateMessageWithTool,
      onToolError: updateMessageWithTool,
      onToken: (token: string, conversationId: string) => {
        setWaitingForFirstUpdate(false);
        setCurrentMessage((prev) => {
          if (!prev) {
            return {
              id: crypto.randomUUID(),
              type: "assistant",
              content: token,
              timestamp: Date.now(),
              isStreaming: true,
              segments: [
                { kind: "text", id: crypto.randomUUID(), text: token },
              ],
            };
          }
          const segments = prev.segments ? [...prev.segments] : [];
          const last = segments[segments.length - 1];
          if (last && last.kind === "text") {
            segments[segments.length - 1] = {
              ...last,
              text: last.text + token,
            };
          } else {
            segments.push({
              kind: "text",
              id: crypto.randomUUID(),
              text: token,
            });
          }

          return {
            ...prev,
            content: prev.content + token,
            segments,
          };
        });
      },

      onError: (errorMsg: string) => {
        setError(errorMsg);
        setIsStreaming(false);
        setWaitingForFirstUpdate(false);
      },

      onComplete: () => {
        if (hasFinalizedRef.current) return;
        hasFinalizedRef.current = true;

        setIsStreaming(false);

        setCurrentMessage((prev) => {
          if (prev) {
            const finalMessage = {
              ...prev,
              isStreaming: false,
            };
            setMessages((msgs) => {
              const last = msgs[msgs.length - 1];
              if (
                last &&
                last.type === "assistant" &&
                last.content === finalMessage.content
              ) {
                return msgs;
              }
              return [...msgs, finalMessage];
            });
          }
          return null;
        });
      },

      onReady: (runId: string) => {
        setCurrentRunId(runId);
      },
    });

    return () => {
      chatServiceRef.current?.disconnect();
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    const fetchConversation = async () => {
      try {
        const res = await fetch(`/api/conversation/${conversationId}`, {
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = await res.json();
        const msgs = Array.isArray(data?.messages) ? data.messages : [];
        if (!isMounted) return;

        const hydrated: ChatMessageType[] = msgs.map((m: any) => {
          if (m.type === "assistant" && m.segments && m.segments.length > 0) {
            return {
              id: m.id || crypto.randomUUID(),
              type: "assistant",
              content: m.content || "",
              timestamp: m.timestamp || Date.now(),
              isStreaming: !!m.isStreaming,
              segments: m.segments,
            };
          }
          return {
            id: m.id || crypto.randomUUID(),
            type: m.type,
            content: m.content || "",
            timestamp: m.timestamp || Date.now(),
          };
        });

        setMessages((prev) => (prev.length > 0 ? prev : hydrated));
      } catch (e) {
        void e;
      }
    };
    fetchConversation();
    return () => {
      isMounted = false;
    };
  }, [conversationId]);

  const handleCancel = useCallback(async () => {
    try {
      if (!currentRunId) {
        return;
      }
      await stopConversation(conversationId, currentRunId);
    } catch (e) {
    } finally {
      setIsStreaming(false);
      setWaitingForFirstUpdate(false);
      setCurrentRunId(null);
      setCurrentMessage((prev) => {
        if (!prev) return null;
        const hasContent =
          (prev.content && prev.content.trim().length > 0) ||
          (Array.isArray(prev.segments) && prev.segments.length > 0);
        if (hasContent) {
          const finalMessage = {
            ...prev,
            isStreaming: false,
          } as ChatMessageType;
          setMessages((msgs) => {
            const last = msgs[msgs.length - 1];
            if (
              last &&
              last.type === "assistant" &&
              last.content === finalMessage.content
            ) {
              return msgs;
            }
            return [...msgs, finalMessage];
          });
        }
        return null;
      });
      chatServiceRef.current?.disconnect();
      hasFinalizedRef.current = true;
    }
  }, [conversationId, currentRunId]);

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;

      let didCancel = false;
      if (isStreaming) {
        await handleCancel();
        didCancel = true;

        hasFinalizedRef.current = false;
        setError(null);
        setCurrentMessage(null);
        setCurrentRunId(null);

        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      if (!didCancel) {
        setError(null);
        setCurrentMessage(null);
        setCurrentRunId(null);
        hasFinalizedRef.current = false;
      }

      setIsStreaming(true);
      setWaitingForFirstUpdate(true);
      setIsAtBottom(true);

      const userMessage = {
        id: crypto.randomUUID(),
        type: "user" as const,
        content: message.trim(),
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMessage]);

      const allMessages = [...messages, userMessage];
      const chatMessages: ChatMessage[] = allMessages.map((msg) => ({
        id: msg.id,
        type: msg.type,
        content: msg.content,
        timestamp: msg.timestamp,
      }));

      try {
        await chatServiceRef.current?.startStream(chatMessages, conversationId);
      } catch (error) {
        setError(
          error instanceof Error ? error.message : "Failed to start stream"
        );
        setIsStreaming(false);
      }
    },
    [messages, isStreaming, handleCancel]
  );

  useEffect(() => {
    const key = `initialMessage:${conversationId}`;
    const pending =
      typeof window !== "undefined" ? sessionStorage.getItem(key) : null;
    if (pending && messages.length === 0) {
      sessionStorage.removeItem(key);
      handleSendMessage(pending);
    }
  }, [conversationId, handleSendMessage, messages.length]);

  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!inputValue.trim()) return;

      handleSendMessage(inputValue);
      setInputValue("");
    },
    [inputValue, handleSendMessage]
  );

  const handleApprovalAction = useCallback(
    async (callId: string, approve: boolean, reason?: string) => {
      try {
        setError(null);
        setIsStreaming(true);
        hasFinalizedRef.current = false;

        await chatServiceRef.current?.startApprovalStream(
          callId,
          approve,
          reason,
          conversationId
        );
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : `Failed to ${approve ? "approve" : "deny"} tool call`
        );
        setIsStreaming(false);
        throw error;
      }
    },
    []
  );

  return (
    <div className="relative h-full w-full">
      <div
        ref={scrollContainerRef}
        onScroll={(e) => {
          const target = e.currentTarget;
          const threshold = 40;
          const currentTop = target.scrollTop;
          const delta = currentTop - lastScrollTopRef.current;
          lastScrollTopRef.current = currentTop;

          if (delta < 0) {
            setIsAtBottom(false);
            return;
          }

          const atBottom =
            target.scrollTop + target.clientHeight >=
            target.scrollHeight - threshold;
          if (atBottom) {
            setIsAtBottom(true);
          }
        }}
        className="h-full overflow-auto py-4 pb-16"
      >
        <div className="max-w-5xl mx-auto">
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
              <strong>Error:</strong> {error}
            </div>
          )}

          <ChatMessages
            messages={messages}
            currentMessage={currentMessage}
            isStreaming={isStreaming}
            waitingForFirstUpdate={waitingForFirstUpdate}
            autoScroll={isAtBottom}
            onApprovalAction={handleApprovalAction}
          />
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 w-full max-w-5xl mx-auto px-4">
        <div className="xs:ml-[0px] ml-[-8px] bg-dark rounded-t-3xl">
          <ChatInput
            inputValue={inputValue}
            setInputValue={setInputValue}
            handleSubmit={handleSubmit}
            isStreaming={isStreaming}
            hasMessages={messages.length > 0}
            onCancel={handleCancel}
          />
        </div>
      </div>
    </div>
  );
}
