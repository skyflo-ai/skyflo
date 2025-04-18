import { useRef, useEffect, useState, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import { getAuthHeaders } from "@/lib/api";

interface UseWebSocketProps {
  conversationId?: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
  onMessage?: (data: any) => void;
  onAgentUpdate?: (data: any) => void;
  onPlannerStart?: (data: any) => void;
  onPlannerProgress?: (data: any) => void;
  onPlannerComplete?: (data: any) => void;
  onExecutorStart?: (data: any) => void;
  onExecutorProgress?: (data: any) => void;
  onStepUpdate?: (data: any) => void;
  onStepComplete?: (data: any) => void;
  onTerminalOutput?: (data: any) => void;
  onVerifierStart?: (data: any) => void;
  onVerifierProgress?: (data: any) => void;
  onVerifierComplete?: (data: any) => void;
  onWorkflowComplete?: (data: any) => void;
  onPlan?: (data: any) => void;
  onVerificationCriteria?: (data: any) => void;
  onCriterionChecking?: (data: any) => void;
  onCriterionResult?: (data: any) => void;
  onVerificationComplete?: (data: any) => void;
}

export function useWebSocket({
  conversationId,
  onConnect,
  onDisconnect,
  onError,
  onMessage,
  onAgentUpdate,
  onPlannerStart,
  onPlannerProgress,
  onPlannerComplete,
  onExecutorStart,
  onExecutorProgress,
  onStepUpdate,
  onStepComplete,
  onTerminalOutput,
  onVerifierStart,
  onVerifierProgress,
  onVerifierComplete,
  onWorkflowComplete,
  onPlan,
  onVerificationCriteria,
  onCriterionChecking,
  onCriterionResult,
  onVerificationComplete,
}: UseWebSocketProps) {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReconnectButton, setShowReconnectButton] = useState(false);
  // Add references for reconnection management
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const maxReconnectAttempts = 10;
  const lastConversationIdRef = useRef<string | undefined>(conversationId);
  // Create a Map to track cleanup registration status for socket instances
  const cleanupRegisteredRef = useRef<Map<Socket, boolean>>(new Map());
  // Add connection initialization tracking
  const connectionInitializedRef = useRef<Record<string, boolean>>({});

  const setupSocketHandlers = useCallback(
    (socket: Socket) => {
      socket.on("connected", (event) => {
        setIsConnected(true);
        setError(null);
        setShowReconnectButton(false);
        reconnectAttemptRef.current = 0;
        onConnect?.();

        // Start heartbeat once connected
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
        }
        heartbeatIntervalRef.current = setInterval(() => {
          if (socket.connected) {
            socket.emit("ping", { timestamp: Date.now() });
          }
        }, 15000); // Send heartbeat every 15 seconds
      });

      socket.on("disconnect", () => {
        setIsConnected(false);
        setShowReconnectButton(true);

        // Clear heartbeat on disconnect
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        onDisconnect?.();

        // Attempt automatic reconnection
        if (
          lastConversationIdRef.current &&
          !lastConversationIdRef.current.startsWith("temp-")
        ) {
          handleReconnect(lastConversationIdRef.current);
        }
      });

      socket.on("connect_error", (error) => {
        console.error("[WebSocket] Connection error:", error);
        setError(`Connection error: ${error.message}`);
        setIsConnected(false);
        onError?.(error);

        // Attempt automatic reconnection for connection errors
        if (
          lastConversationIdRef.current &&
          !lastConversationIdRef.current.startsWith("temp-")
        ) {
          handleReconnect(lastConversationIdRef.current);
        }
      });

      socket.on("error", (event) => {
        console.error("[WebSocket] Error:", event);
        onError?.(event);
      });

      // Add pong handler for heartbeat responses
      socket.on("pong", (data) => {
        const latency = Date.now() - (data.timestamp || 0);
        // Reset connection if latency is extremely high (possible zombie connection)
        if (latency > 10000) {
          // 10 seconds
          console.warn(
            "[WebSocket] High latency detected, resetting connection"
          );
          socket.disconnect();
          // Connection will auto-reconnect from the disconnect handler
        }
      });

      socket.on("message", (event) => {
        onMessage?.(event);
      });

      socket.on("agent_update", (event) => {
        onAgentUpdate?.(event);
      });

      socket.on("planner_start", (event) => {
        onPlannerStart?.(event);
      });

      socket.on("planner_progress", (event) => {
        onPlannerProgress?.(event);
      });

      socket.on("planner_complete", (event) => {
        onPlannerComplete?.(event);
      });

      socket.on("executor_start", (event) => {
        onExecutorStart?.(event);
      });

      socket.on("executor_progress", (event) => {
        onExecutorProgress?.(event);
      });

      socket.on("step_update", (event) => {
        onStepUpdate?.(event);
      });

      socket.on("step_complete", (event) => {
        onStepComplete?.(event);
      });

      socket.on("terminal_output", (event) => {
        onTerminalOutput?.(event);
      });

      socket.on("verifier_start", (event) => {
        onVerifierStart?.(event);
      });

      socket.on("verifier_progress", (event) => {
        onVerifierProgress?.(event);
      });

      socket.on("verifier_complete", (event) => {
        onVerifierComplete?.(event);
      });

      socket.on("workflow_complete", (event) => {
        onWorkflowComplete?.(event);
      });

      socket.on("plan", (event) => {
        onPlan?.(event);
      });

      socket.on("verification_criteria_list", (event) => {
        onVerificationCriteria?.(event);
      });

      socket.on("criterion_checking", (event) => {
        onCriterionChecking?.(event);
      });

      socket.on("criterion_result", (event) => {
        onCriterionResult?.(event);
      });

      socket.on("verification_complete", (event) => {
        onVerificationComplete?.(event);
      });
    },
    [
      onConnect,
      onDisconnect,
      onError,
      onMessage,
      onAgentUpdate,
      onPlannerStart,
      onPlannerProgress,
      onPlannerComplete,
      onExecutorStart,
      onExecutorProgress,
      onStepUpdate,
      onStepComplete,
      onTerminalOutput,
      onVerifierStart,
      onVerifierProgress,
      onVerifierComplete,
      onWorkflowComplete,
      onPlan,
      onVerificationCriteria,
      onCriterionChecking,
      onCriterionResult,
      onVerificationComplete,
    ]
  );

  // New function to handle reconnection attempts with exponential backoff
  const handleReconnect = useCallback((conversationId: string) => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }

    // If we've reached max attempts, show reconnect button and stop trying
    if (reconnectAttemptRef.current >= maxReconnectAttempts) {
      setShowReconnectButton(true);
      return;
    }

    // Calculate backoff delay with jitter to prevent all clients reconnecting at the same time
    const baseDelay = Math.min(
      1000 * Math.pow(1.5, reconnectAttemptRef.current),
      30000
    );
    const jitter = Math.random() * 1000;
    const delay = baseDelay + jitter;

    reconnectTimerRef.current = setTimeout(() => {
      reconnectAttemptRef.current++;
      connectToWebSocket(conversationId);
    }, delay);
  }, []);

  const connectToWebSocket = useCallback(
    async (conversationId: string) => {
      if (!conversationId || conversationId.startsWith("temp-")) return null;

      try {
        // Get WebSocket URL
        const wsUrl = process.env.WEB_SOCKET_URL || "ws://localhost:8000";
        const socketUrl = wsUrl.startsWith("ws")
          ? wsUrl.replace("ws://", "http://").replace("wss://", "https://")
          : wsUrl;

        // Check if we already have a connection to this conversation
        if (
          socketRef.current?.connected &&
          socketRef.current.io.opts.query?.conversation_id === conversationId
        ) {
          return socketRef.current;
        }

        // Get authentication headers to extract token
        const authHeaders = await getAuthHeaders();
        const authToken = authHeaders.Authorization
          ? authHeaders.Authorization.replace("Bearer ", "")
          : null;

        // Disconnect existing socket if any
        if (socketRef.current) {
          // Clear any pending cleanup for the old socket
          if (cleanupRegisteredRef.current.get(socketRef.current)) {
            cleanupRegisteredRef.current.delete(socketRef.current);
          }

          socketRef.current.disconnect();
          socketRef.current = null;
        }

        // Create new socket connection with settings matching the server configuration
        socketRef.current = io(socketUrl, {
          path: `/socket.io`,
          transports: ["websocket", "polling"], // Allow both WebSocket and polling transports
          query: {
            conversation_id: conversationId,
            token: authToken, // Add token to query params for WebSocket auth
          },
          autoConnect: true,
          reconnection: true,
          reconnectionAttempts: 10,
          reconnectionDelay: 1000,
          reconnectionDelayMax: 5000,
          timeout: 20000, // 20 seconds connection timeout

          // Use forceNew to ensure a clean connection
          forceNew: true, // Force a new connection to avoid reusing connections
          withCredentials: true, // Include credentials in cross-origin requests
        } as any); // Type assertion to bypass TypeScript constraints

        // Add connection debug listeners
        socketRef.current.io.on("error", (error: any) => {
          console.error("[WebSocket] Socket.io manager error:", error);
        });

        socketRef.current.io.on("reconnect_attempt", (attempt: number) => {
          console.log(
            `[WebSocket] Socket.io manager reconnect attempt ${attempt}`
          );
        });

        socketRef.current.io.on("reconnect_failed", () => {
          console.error("[WebSocket] Socket.io manager reconnect failed");
        });

        // Store the conversation ID for reconnection purposes
        lastConversationIdRef.current = conversationId;

        // Setup event handlers
        setupSocketHandlers(socketRef.current);

        return socketRef.current;
      } catch (error) {
        console.error("[WebSocket] Failed to initialize Socket.IO:", error);
        setError(`Failed to connect: ${error}`);
        // Attempt reconnection after error
        handleReconnect(conversationId);
        return null;
      }
    },
    [setupSocketHandlers, handleReconnect]
  );

  // Reconnect to WebSocket with a new conversation ID
  const reconnect = useCallback(
    async (newConversationId: string) => {
      // Reset reconnect attempts for explicit reconnection
      reconnectAttemptRef.current = 0;
      return await connectToWebSocket(newConversationId);
    },
    [connectToWebSocket]
  );

  // Initialize WebSocket connection when conversationId changes
  useEffect(() => {
    // Add connection tracking to prevent multiple simultaneous connections
    let isConnecting = false;
    let unmounted = false;

    if (
      conversationId &&
      !conversationId.startsWith("temp-") &&
      !isConnecting &&
      !connectionInitializedRef.current[conversationId] // Only initialize once per conversation ID
    ) {
      // Mark this conversation as initialized
      connectionInitializedRef.current[conversationId] = true;
      isConnecting = true;
      lastConversationIdRef.current = conversationId;

      // Add debounce to prevent rapid connection attempts
      const timer = setTimeout(() => {
        if (unmounted) return; // Don't connect if unmounted

        connectToWebSocket(conversationId).finally(() => {
          if (!unmounted) {
            // Only update state if not unmounted
            isConnecting = false;
          }
        });
      }, 300);

      return () => {
        clearTimeout(timer);
        unmounted = true;
        isConnecting = false;
      };
    }

    // Only disconnect on component unmount, not on every conversationId change
    return () => {
      unmounted = true;

      // Cleanup all intervals and timers on unmount
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      // For component re-render, don't disconnect immediately
      // Only disconnect on full unmount (component removal from DOM)
      if (socketRef.current) {
        // Let the socket stay alive a bit longer to receive pending messages
        const socket = socketRef.current;

        // Only register this cleanup once using our Map
        if (!cleanupRegisteredRef.current.get(socket)) {
          cleanupRegisteredRef.current.set(socket, true);

          // Using a larger timeout to ensure we don't disconnect during quick remounts
          setTimeout(() => {
            // Check if the socket is still the current one before disconnecting
            if (socketRef.current === socket) {
              socket.disconnect();
              socketRef.current = null;
              // Clean up our tracking Map
              cleanupRegisteredRef.current.delete(socket);
            } else {
              // Still clean up our tracking Map for the old socket
              cleanupRegisteredRef.current.delete(socket);
            }
          }, 2000); // Longer delay to handle remounts
        }
      }
    };
  }, [conversationId, connectToWebSocket]);

  // Add stable connection reference tracking to handle React re-renders
  useEffect(() => {
    // This effect ensures we keep the connection across re-renders
    return () => {
      // This runs on full component unmount (not just re-renders)
      // Clear the cleanup tracking Map on full unmount
      cleanupRegisteredRef.current.clear();
    };
  }, []);

  return {
    socket: socketRef.current,
    isConnected,
    error,
    showReconnectButton,
    reconnect,
  };
}
