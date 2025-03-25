import { io, Socket } from "socket.io-client";
import { getAuthHeaders } from "@/lib/api";
import {
  SocketEvent,
  ChatState,
  ChatStateUpdate,
  Plan,
  PlanStep,
  AgentState,
} from "@/lib/types/chat";

/**
 * Socket service for managing WebSocket connections and events
 */
class SocketService {
  private socket: Socket | null = null;
  private eventBuffer: SocketEvent[] = [];
  private lastProcessedTimestamp = 0;
  private processingInterval: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private readonly MAX_RECONNECT_ATTEMPTS = 5;
  private readonly RECONNECT_DELAY = 1000;
  private readonly EVENT_PROCESSING_INTERVAL = 100; // ms

  private stateUpdateCallback: ((update: ChatStateUpdate) => void) | null =
    null;
  private debugCallback: ((message: string, data?: any) => void) | null = null;

  /**
   * Initialize socket connection
   * @param url WebSocket server URL
   * @param conversationId Current conversation ID
   * @param onStateUpdate Callback for state updates
   * @param onDebug Debug message callback
   */
  async initialize(
    url: string,
    conversationId: string,
    onStateUpdate: (update: ChatStateUpdate) => void,
    onDebug?: (message: string, data?: any) => void
  ) {
    this.stateUpdateCallback = onStateUpdate;
    this.debugCallback = onDebug || console.log;

    this.debug("Initializing socket connection", { url, conversationId });

    try {
      const authHeaders = await getAuthHeaders();
      const authToken = authHeaders.Authorization?.replace("Bearer ", "");

      this.socket = io(url, {
        path: "/socket.io",
        transports: ["websocket"],
        query: {
          conversation_id: conversationId,
          token: authToken,
        },
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: this.MAX_RECONNECT_ATTEMPTS,
        reconnectionDelay: this.RECONNECT_DELAY,
      });

      this.setupEventHandlers();
      this.startEventProcessing();

      this.debug("Socket connection initialized");
    } catch (error) {
      this.debug("Failed to initialize socket", error);
      throw error;
    }
  }

  /**
   * Set up socket event handlers
   */
  private setupEventHandlers() {
    if (!this.socket) return;

    // Connection events
    this.socket.on("connect", () => {
      this.debug("Socket connected");
      this.reconnectAttempts = 0;
      this.updateState({
        type: "CONNECTION_STATUS",
        payload: { isConnected: true },
        timestamp: Date.now(),
      });
    });

    this.socket.on("disconnect", (reason) => {
      this.debug("Socket disconnected", { reason });
      this.updateState({
        type: "CONNECTION_STATUS",
        payload: { isConnected: false },
        timestamp: Date.now(),
      });
    });

    this.socket.on("connect_error", (error) => {
      this.debug("Socket connection error", error);
      this.handleReconnect();
    });

    // Plan execution events
    this.socket.on("planner_start", (event: SocketEvent) => {
      this.debug("Planner started", event);
      this.bufferEvent({
        ...event,
        type: "PLANNER_START",
        timestamp: Date.now(),
      });
    });

    this.socket.on("planner_complete", (event: SocketEvent) => {
      this.debug("Planner completed", event);
      this.bufferEvent({
        ...event,
        type: "PLANNER_COMPLETE",
        timestamp: Date.now(),
      });
    });

    this.socket.on("executor_progress", (event: SocketEvent) => {
      this.debug("Executor progress", event);
      this.bufferEvent({
        ...event,
        type: "EXECUTOR_PROGRESS",
        timestamp: Date.now(),
      });
    });

    this.socket.on("step_output", (event: SocketEvent) => {
      this.debug("Step output received", event);
      this.bufferEvent({
        ...event,
        type: "STEP_OUTPUT",
        timestamp: Date.now(),
      });
    });

    this.socket.on("step_complete", (event: SocketEvent) => {
      this.debug("Step completed", event);
      this.bufferEvent({
        ...event,
        type: "STEP_COMPLETE",
        timestamp: Date.now(),
      });
    });

    this.socket.on("step_failed", (event: SocketEvent) => {
      this.debug("Step failed", event);
      this.bufferEvent({
        ...event,
        type: "STEP_FAILED",
        timestamp: Date.now(),
      });
    });

    this.socket.on("plan_failed", (event: SocketEvent) => {
      this.debug("Plan failed", event);
      this.bufferEvent({
        ...event,
        type: "PLAN_FAILED",
        timestamp: Date.now(),
      });
    });

    this.socket.on("verifier_start", (event: SocketEvent) => {
      this.debug("Verifier started", event);
      this.bufferEvent({
        ...event,
        type: "VERIFIER_START",
        timestamp: Date.now(),
      });
    });

    this.socket.on("verifier_complete", (event: SocketEvent) => {
      this.debug("Verifier completed", event);
      this.bufferEvent({
        ...event,
        type: "VERIFIER_COMPLETE",
        timestamp: Date.now(),
      });
    });

    this.socket.on("message", (event: SocketEvent) => {
      this.debug("Message received", event);
      this.bufferEvent({
        ...event,
        type: "MESSAGE",
        timestamp: Date.now(),
      });
    });
  }

  /**
   * Buffer an event for ordered processing
   */
  private bufferEvent(event: SocketEvent) {
    this.eventBuffer.push(event);
    this.eventBuffer.sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Start processing buffered events
   */
  private startEventProcessing() {
    if (this.processingInterval) return;

    this.processingInterval = setInterval(() => {
      this.processEventBuffer();
    }, this.EVENT_PROCESSING_INTERVAL);
  }

  /**
   * Process buffered events in order
   */
  private processEventBuffer() {
    while (this.eventBuffer.length > 0) {
      const event = this.eventBuffer[0];

      // Skip if event is too early (out of order)
      if (event.timestamp < this.lastProcessedTimestamp) {
        this.debug("Skipping out-of-order event", event);
        this.eventBuffer.shift();
        continue;
      }

      this.processEvent(event);
      this.lastProcessedTimestamp = event.timestamp;
      this.eventBuffer.shift();
    }
  }

  /**
   * Process a single event and update state
   */
  private processEvent(event: SocketEvent) {
    const timestamp = Date.now();

    switch (event.type) {
      case "PLANNER_START":
        this.updateState({
          type: "PLANNER_START",
          payload: {
            agentState: AgentState.PLANNING,
            currentPhase: "planning",
            progress: 0.1,
          },
          timestamp,
        });
        break;

      case "PLANNER_COMPLETE":
        if (event.data?.plan) {
          const plan: Plan = {
            ...event.data.plan,
            steps: event.data.plan.steps.map((step: PlanStep) => ({
              ...step,
              status: "pending",
            })),
            created_at: timestamp,
            updated_at: timestamp,
          };

          this.updateState({
            type: "PLANNER_COMPLETE",
            payload: {
              currentPlan: plan,
              agentState: AgentState.EXECUTING,
              currentPhase: "executing",
              progress: 0.3,
            },
            timestamp,
          });
        }
        break;

      case "EXECUTOR_PROGRESS":
        if (event.data?.step_id) {
          this.updateState({
            type: "EXECUTOR_PROGRESS",
            payload: {
              currentPlan: this.updatePlanStep(event.data.step_id, {
                status: "executing",
              }),
              progress: 0.3 + (event.data.progress || 0) * 0.4,
            },
            timestamp,
          });
        }
        break;

      case "STEP_COMPLETE":
        if (event.data?.step_id) {
          this.updateState({
            type: "STEP_COMPLETE",
            payload: {
              currentPlan: this.updatePlanStep(event.data.step_id, {
                status: "completed",
              }),
            },
            timestamp,
          });
        }
        break;

      case "STEP_FAILED":
        if (event.data?.step_id) {
          this.updateState({
            type: "STEP_FAILED",
            payload: {
              currentPlan: this.updatePlanStep(event.data.step_id, {
                status: "failed",
              }),
              error: event.data.error,
            },
            timestamp,
          });
        }
        break;

      case "PLAN_FAILED":
        this.updateState({
          type: "PLAN_FAILED",
          payload: {
            agentState: AgentState.ERROR,
            currentPhase: "error",
            progress: 1.0,
            error: event.data?.message || "Plan execution failed",
          },
          timestamp,
        });
        break;

      case "VERIFIER_START":
        this.updateState({
          type: "VERIFIER_START",
          payload: {
            agentState: AgentState.VERIFYING,
            currentPhase: "verifying",
            progress: 0.7,
          },
          timestamp,
        });
        break;

      case "VERIFIER_COMPLETE":
        this.updateState({
          type: "VERIFIER_COMPLETE",
          payload: {
            agentState: AgentState.COMPLETED,
            currentPhase: "completed",
            progress: 1.0,
          },
          timestamp,
        });
        break;
    }
  }

  /**
   * Update a step in the current plan
   */
  private updatePlanStep(
    stepId: string,
    update: Partial<PlanStep>
  ): Plan | null {
    const currentState = this.getCurrentState();
    if (!currentState.currentPlan) return null;

    return {
      ...currentState.currentPlan,
      steps: currentState.currentPlan.steps.map((step) =>
        step.step_id === stepId ? { ...step, ...update } : step
      ),
      updated_at: Date.now(),
    };
  }

  /**
   * Get current state from the callback
   */
  private getCurrentState(): ChatState {
    // This should be implemented by the component using the service
    return {
      messages: [],
      currentPlan: null,
      agentState: AgentState.IDLE,
      currentPhase: "",
      progress: 0,
      error: null,
      isConnected: false,
      lastEventTimestamp: 0,
    };
  }

  /**
   * Update state through callback
   */
  private updateState(update: ChatStateUpdate) {
    if (this.stateUpdateCallback) {
      this.stateUpdateCallback(update);
    }
  }

  /**
   * Handle reconnection attempts
   */
  private handleReconnect() {
    this.reconnectAttempts++;
    this.debug("Attempting to reconnect", {
      attempt: this.reconnectAttempts,
      max: this.MAX_RECONNECT_ATTEMPTS,
    });

    if (this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      this.debug("Max reconnection attempts reached");
      this.updateState({
        type: "CONNECTION_ERROR",
        payload: {
          error: "Failed to connect to server after multiple attempts",
          isConnected: false,
        },
        timestamp: Date.now(),
      });
    }
  }

  /**
   * Log debug messages
   */
  private debug(message: string, data?: any) {
    if (this.debugCallback) {
      this.debugCallback(`[SocketService] ${message}`, data);
    }
  }

  /**
   * Send a message to the server
   * @param message Message to send
   */
  sendMessage(message: string) {
    if (!this.socket) {
      this.debug("Cannot send message: Socket not initialized");
      return;
    }

    this.debug("Sending message", { message });
    this.socket.emit("message", { content: message });
  }

  /**
   * Clean up socket connection and intervals
   */
  cleanup() {
    this.debug("Cleaning up socket service");

    if (this.processingInterval) {
      clearInterval(this.processingInterval);
      this.processingInterval = null;
    }

    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }

    this.eventBuffer = [];
    this.lastProcessedTimestamp = 0;
    this.reconnectAttempts = 0;
  }
}

export const socketService = new SocketService();
