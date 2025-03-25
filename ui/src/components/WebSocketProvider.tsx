"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { io, Socket } from "socket.io-client";
import { getWsUrl } from "@/lib/api";

// Create a context for WebSocket
interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  joinConversation: (conversationId: string) => void;
  leaveConversation: (conversationId: string) => void;
  reconnect: () => void;
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";
  lastError: string | null;
}

const WebSocketContext = createContext<WebSocketContextType>({
  socket: null,
  isConnected: false,
  joinConversation: () => {},
  leaveConversation: () => {},
  reconnect: () => {},
  connectionStatus: "disconnected",
  lastError: null,
});

export const useWebSocket = () => useContext(WebSocketContext);

interface WebSocketProviderProps {
  children: ReactNode;
}

// Create a single socket instance outside the component to persist across re-renders
let socketInstance: Socket | null = null;
let currentConversationId: string | null = null;

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected" | "error"
  >("disconnected");
  const [lastError, setLastError] = useState<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const socketRef = useRef<Socket | null>(null);

  // Create WebSocket connection with a conversation ID
  const createSocketConnection = useCallback(
    async (conversationId?: string) => {
      try {
        // We need a conversation ID to connect - either new one or existing one
        const targetConversationId = conversationId || currentConversationId;
        if (!targetConversationId) {
          console.log(
            "[WebSocketProvider] No conversation ID provided and none stored"
          );
          return null;
        }

        // If we're already connected to this conversation, reuse the connection
        if (socketInstance && currentConversationId === targetConversationId) {
          console.log(
            `[WebSocketProvider] Already connected to conversation ${targetConversationId}`
          );
          setupSocketHandlers(socketInstance);
          socketRef.current = socketInstance;
          return socketInstance;
        }

        // Clean up existing socket if connecting to a different conversation
        if (socketInstance) {
          console.log(
            "[WebSocketProvider] Disconnecting from previous conversation"
          );
          socketInstance.removeAllListeners();
          socketInstance.disconnect();
          socketInstance = null;
        }

        // Clear any existing reconnect timeouts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }

        // Update current conversation ID
        currentConversationId = targetConversationId;

        setConnectionStatus("connecting");
        console.log(
          `[WebSocketProvider] Creating new socket connection for conversation ${targetConversationId}`
        );

        // Get WebSocket URL from backend
        const wsUrl = await getWsUrl();

        // Create Socket.IO client with proper configuration
        // IMPORTANT: Include conversation_id in the query parameters
        const newSocket = io(wsUrl, {
          transports: ["websocket", "polling"],
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 1000,
          reconnectionDelayMax: 5000,
          timeout: 20000,
          autoConnect: true,
          forceNew: true,
          path: "/socket.io",
          withCredentials: true,
          query: {
            conversation_id: targetConversationId, // Pass conversation_id in initial connection
          },
        });

        // Store the socket instance globally
        socketInstance = newSocket;
        socketRef.current = newSocket;

        // Setup socket handlers
        setupSocketHandlers(newSocket);

        return newSocket;
      } catch (error) {
        console.error("[WebSocketProvider] Error creating socket:", error);
        setConnectionStatus("error");
        setLastError(
          `Failed to create socket: ${
            error instanceof Error ? error.message : "Unknown error"
          }`
        );
        return null;
      }
    },
    []
  );

  // Setup socket event handlers
  const setupSocketHandlers = useCallback((socket: Socket) => {
    // Clear any existing listeners first
    socket.removeAllListeners();

    socket.on("connect", () => {
      console.log(
        `[WebSocketProvider] Socket connected successfully to conversation ${currentConversationId}`
      );
      setIsConnected(true);
      setConnectionStatus("connected");
      reconnectAttemptsRef.current = 0;
    });

    socket.on("connect_error", (error) => {
      console.error("[WebSocketProvider] Socket connect error:", error);
      setLastError(`Connection error: ${error.message}`);
      setConnectionStatus("error");
    });

    socket.on("disconnect", (reason) => {
      console.warn(`[WebSocketProvider] Socket disconnected: ${reason}`);
      setIsConnected(false);
      setConnectionStatus("disconnected");

      // Handle reconnection for certain disconnect reasons
      if (reason === "io server disconnect" || reason === "transport close") {
        // Server initiated the disconnect or transport closed unexpectedly
        handleReconnect();
      }
    });

    socket.on("error", (error) => {
      console.error("[WebSocketProvider] Socket error:", error);
      setLastError(
        `Socket error: ${typeof error === "string" ? error : "Unknown error"}`
      );
      setConnectionStatus("error");
    });

    // Handler for incoming messages
    socket.on("message", (data) => {
      console.log("[WebSocketProvider] Received message:", data);
    });

    // Use ping-pong to keep connection alive
    socket.io.on("ping", () => {
      console.log("[WebSocketProvider] Received ping from server");
    });

    // Handle the connection status message from the server
    socket.on("connection_status", (data) => {
      console.log("[WebSocketProvider] Connection status:", data);
    });

    // Handle the connected event from the server
    socket.on("connected", (data) => {
      console.log("[WebSocketProvider] Server confirmed connection:", data);
      setIsConnected(true);
      setConnectionStatus("connected");
    });

    // Add extensive debug logging for connection diagnosis
    socket.io.on("open", () => {
      console.log("[WebSocketProvider] Transport connection opened");
    });

    socket.io.on("close", (reason) => {
      console.warn("[WebSocketProvider] Transport connection closed:", reason);
    });

    socket.io.on("error", (error) => {
      console.error("[WebSocketProvider] Transport error:", error);
    });

    // Add a handler or update existing handler for agent_update events to process last_step and answer properties
    socket.on("agent_update", (data) => {
      // Forward the complete event data to any listeners
      socket.emit("agent_update", data);

      // Process last_step and answer properties from the event data
      if (data && data.data) {
        // Log specific attributes that are important for workflow completion
        if (data.data.last_step) {
          console.log("[WebSocketProvider] Workflow last step detected");
        }

        if (data.data.answer) {
          console.log(
            "[WebSocketProvider] Final answer received:",
            data.data.answer.substring(0, 100) +
              (data.data.answer.length > 100 ? "..." : "")
          );
        }
      }
    });
  }, []);

  // Handle reconnection with exponential backoff
  const handleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.error("[WebSocketProvider] Max reconnection attempts reached");
      setLastError(
        "Maximum reconnection attempts reached. Please refresh the page."
      );
      return;
    }

    reconnectAttemptsRef.current += 1;
    const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000); // exponential backoff capped at 30s

    console.log(
      `[WebSocketProvider] Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
    );

    reconnectTimeoutRef.current = setTimeout(() => {
      if (currentConversationId) {
        createSocketConnection(currentConversationId);
      }
    }, delay);
  }, [createSocketConnection]);

  // Public API for reconnecting
  const reconnect = useCallback(() => {
    console.log("[WebSocketProvider] Manual reconnection requested");
    reconnectAttemptsRef.current = 0; // Reset counter for manual reconnect

    if (currentConversationId) {
      createSocketConnection(currentConversationId);
    } else {
      console.warn(
        "[WebSocketProvider] Cannot reconnect without conversation ID"
      );
    }
  }, [createSocketConnection]);

  // Join a conversation - now creates a new socket with the conversation ID
  const joinConversation = useCallback(
    (conversationId: string) => {
      console.log(
        `[WebSocketProvider] Joining conversation: ${conversationId}`
      );
      createSocketConnection(conversationId);
    },
    [createSocketConnection]
  );

  // Leave a conversation
  const leaveConversation = useCallback((conversationId: string) => {
    console.log(`[WebSocketProvider] Leaving conversation: ${conversationId}`);

    // Only disconnect if we're leaving the current conversation
    if (conversationId === currentConversationId) {
      if (socketInstance) {
        console.log(
          `[WebSocketProvider] Disconnecting from conversation ${conversationId}`
        );
        socketInstance.disconnect();
        socketInstance = null;
      }

      currentConversationId = null;
      setIsConnected(false);
      setConnectionStatus("disconnected");
    }
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      console.log("[WebSocketProvider] Cleaning up WebSocket provider");
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      // When provider unmounts, we SHOULD disconnect the socket
      if (socketInstance) {
        socketInstance.removeAllListeners();
        socketInstance.disconnect();
        socketInstance = null;
      }

      currentConversationId = null;
    };
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        socket: socketInstance,
        isConnected,
        joinConversation,
        leaveConversation,
        reconnect,
        connectionStatus,
        lastError,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}
