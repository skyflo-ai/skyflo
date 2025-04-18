import { io, Socket } from "socket.io-client";
import {
  AgentUpdate,
  MessageData,
  Plan,
  StepUpdate,
  VerificationCriteria,
  VerificationResult,
} from "../types";

export class WebSocketService {
  private socket: Socket | null = null;
  private handlers: {
    onAgentUpdate?: (data: AgentUpdate) => void;
    onMessage?: (data: MessageData) => void;
    onError?: (error: Error) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onPlan?: (data: Plan) => void;
    onStepUpdate?: (data: StepUpdate) => void;
    onVerificationCriteriaList?: (data: VerificationCriteria[]) => void;
    onVerificationResult?: (data: VerificationResult) => void;
  } = {};

  constructor(private baseUrl: string) {}

  connect(conversationId: string): Promise<Socket> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = io(this.baseUrl, {
          path: "/socket.io",
          query: { conversation_id: conversationId },
          transports: ["websocket"],
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 1000,
        });

        this.setupEventListeners();
        resolve(this.socket);
      } catch (error) {
        reject(error);
      }
    });
  }

  private setupEventListeners() {
    if (!this.socket) return;

    this.socket.on("connect", () => {
      this.handlers.onConnect?.();
    });

    this.socket.on("disconnect", () => {
      this.handlers.onDisconnect?.();
    });

    this.socket.on("agent_update", (data: AgentUpdate) => {
      this.handlers.onAgentUpdate?.(data);
    });

    this.socket.on("message", (data: MessageData) => {
      this.handlers.onMessage?.(data);
    });

    this.socket.on("error", (error: Error) => {
      console.error("WebSocket error:", error);
      this.handlers.onError?.(error);
    });

    this.socket.on("plan", (data: any) => {
      if (data.data?.plan) {
        this.handlers.onPlan?.(data.data.plan);
      }
    });

    this.socket.on("plan_generated", (data: any) => {
      if (data.details?.plan) {
        this.handlers.onPlan?.(data.details.plan);
      }
    });

    this.socket.on("step_update", (data: any) => {
      if (data.data) {
        this.handlers.onStepUpdate?.(data.data);
      }
    });

    this.socket.on("verification_criteria_list", (data: any) => {
      if (data.data?.details?.criteria) {
        this.handlers.onVerificationCriteriaList?.(data.data.details.criteria);
      }
    });

    this.socket.on("criterion_result", (data: any) => {
      if (data.data?.details) {
        this.handlers.onVerificationResult?.(data.data.details);
      }
    });
  }

  setHandlers(handlers: typeof this.handlers) {
    this.handlers = handlers;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  getSocket(): Socket | null {
    return this.socket;
  }

  async reconnect(conversationId: string): Promise<void> {
    this.disconnect();
    await this.connect(conversationId);
  }

  emit(event: string, data: any) {
    if (this.socket && this.isConnected()) {
      this.socket.emit(event, data);
    } else {
      console.error("Cannot emit event: socket is not connected");
    }
  }
}
