"use client";

import React, {
  createContext,
  useContext,
  useRef,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { io, Socket } from "socket.io-client";

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

// Persist socket instance across re-renders
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

  const createSocketConnection = useCallback(async () => {
    try {
      if (socketInstance) {
        setupSocketHandlers(socketInstance);
        socketRef.current = socketInstance;
        return socketInstance;
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      setConnectionStatus("connecting");

      // Configure Socket.IO client with proper settings
      const newSocket = io("", {
        transports: ["websocket", "polling"],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 20000,
        autoConnect: true,
        forceNew: true,
        path: "/api/ws/socket.io",
        withCredentials: true,
      });

      socketInstance = newSocket;
      socketRef.current = newSocket;
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
  }, []);

  const setupSocketHandlers = useCallback((socket: Socket) => {
    socket.removeAllListeners();

    socket.on("connect", () => {
      setIsConnected(true);
      setConnectionStatus("connected");
      reconnectAttemptsRef.current = 0;

      // Rejoin the current conversation if there is one
      if (currentConversationId) {
        socket.emit("join_conversation", {
          conversation_id: currentConversationId,
        });
      }
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

      if (reason === "io server disconnect" || reason === "transport close") {
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

    socket.on("message", (data) => {
      console.log("[WebSocketProvider] Received message:", data);
    });

    socket.io.on("ping", () => {
      console.log("[WebSocketProvider] Received ping from server");
    });

    socket.on("connection_status", (data) => {
      console.log("[WebSocketProvider] Connection status:", data);
    });

    socket.on("connected", (data) => {
      console.log("[WebSocketProvider] Server confirmed connection:", data);
      setIsConnected(true);
      setConnectionStatus("connected");
    });

    socket.io.on("open", () => {
      console.log("[WebSocketProvider] Transport connection opened");
    });

    socket.io.on("close", (reason) => {
      console.warn("[WebSocketProvider] Transport connection closed:", reason);
    });

    socket.io.on("error", (error) => {
      console.error("[WebSocketProvider] Transport error:", error);
    });

    socket.on("agent_update", (data) => {
      if (data && data.data) {
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

  const handleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.error("[WebSocketProvider] Max reconnection attempts reached");
      setLastError(
        "Maximum reconnection attempts reached. Please refresh the page."
      );
      return;
    }

    reconnectAttemptsRef.current += 1;
    const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000);

    reconnectTimeoutRef.current = setTimeout(() => {
      createSocketConnection();
    }, delay);
  }, [createSocketConnection]);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    createSocketConnection();
  }, [createSocketConnection]);

  const joinConversation = useCallback(
    (conversationId: string) => {
      currentConversationId = conversationId;

      if (!socketInstance) {
        createSocketConnection();
      } else {
        socketInstance.emit("join_conversation", {
          conversation_id: conversationId,
        });
      }
    },
    [createSocketConnection]
  );

  const leaveConversation = useCallback((conversationId: string) => {
    if (conversationId === currentConversationId) {
      if (socketInstance) {
        socketInstance.emit("leave_conversation", {
          conversation_id: conversationId,
        });
      }
      currentConversationId = null;
    }
  }, []);

  // Initialize socket connection when provider mounts
  React.useEffect(() => {
    createSocketConnection();
    return () => {
      if (socketInstance) {
        socketInstance.disconnect();
        socketInstance = null;
      }
    };
  }, [createSocketConnection]);

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
