import {
  ChatState,
  ChatStateUpdate,
  ChatMessage,
  Plan,
  AgentState,
} from "@/lib/types/chat";

/**
 * Chat state manager for handling state updates and maintaining chat history
 */
class ChatStateManager {
  private state: ChatState;
  private stateUpdateCallbacks: ((state: ChatState) => void)[] = [];
  private debugCallback: ((message: string, data?: any) => void) | null = null;

  constructor() {
    this.state = this.getInitialState();
  }

  /**
   * Initialize the state manager
   * @param onStateUpdate Callback for state updates
   * @param onDebug Debug message callback
   */
  initialize(
    onStateUpdate: (state: ChatState) => void,
    onDebug?: (message: string, data?: any) => void
  ) {
    this.stateUpdateCallbacks.push(onStateUpdate);
    this.debugCallback = onDebug || console.log;
    this.debug("State manager initialized");
  }

  /**
   * Get initial state
   */
  private getInitialState(): ChatState {
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
   * Get current state
   */
  getState(): ChatState {
    return { ...this.state };
  }

  /**
   * Handle state updates from socket service
   */
  handleStateUpdate(update: ChatStateUpdate) {
    this.debug("Handling state update", update);

    const { type, payload, timestamp } = update;

    // Skip if update is older than last processed
    if (timestamp < this.state.lastEventTimestamp) {
      this.debug("Skipping outdated update", {
        timestamp,
        lastProcessed: this.state.lastEventTimestamp,
      });
      return;
    }

    // Update state based on update type
    switch (type) {
      case "CONNECTION_STATUS":
        this.updateState({
          isConnected: payload.isConnected,
          error: payload.error || null,
        });
        break;

      case "CONNECTION_ERROR":
        this.updateState({
          isConnected: false,
          error: payload.error || "Connection error",
        });
        break;

      case "PLANNER_START":
        this.updateState({
          agentState: payload.agentState,
          currentPhase: payload.currentPhase,
          progress: payload.progress,
          error: null,
        });
        break;

      case "PLANNER_COMPLETE":
        if (payload.currentPlan) {
          this.addMessage({
            id: `plan-${Date.now()}`,
            from: "sky",
            plan: payload.currentPlan,
            timestamp: Date.now(),
          });
        }
        this.updateState({
          currentPlan: payload.currentPlan,
          agentState: payload.agentState,
          currentPhase: payload.currentPhase,
          progress: payload.progress,
        });
        break;

      case "EXECUTOR_PROGRESS":
        this.updateState({
          currentPlan: payload.currentPlan || this.state.currentPlan,
          progress: payload.progress,
        });
        break;

      case "STEP_COMPLETE":
      case "STEP_FAILED":
        this.updateState({
          currentPlan: payload.currentPlan || this.state.currentPlan,
          error: payload.error || null,
        });
        break;

      case "PLAN_FAILED":
        if (payload.error) {
          this.addMessage({
            id: `error-${Date.now()}`,
            from: "sky",
            message: `❌ **Error:** ${payload.error}`,
            timestamp: Date.now(),
          });
        }
        this.updateState({
          agentState: payload.agentState,
          currentPhase: payload.currentPhase,
          progress: payload.progress,
          error: payload.error || "Plan execution failed",
        });
        break;

      case "VERIFIER_START":
      case "VERIFIER_COMPLETE":
        this.updateState({
          agentState: payload.agentState,
          currentPhase: payload.currentPhase,
          progress: payload.progress,
        });
        break;

      case "MESSAGE":
        const messagePayload = payload as { content: string };
        if ("content" in messagePayload && messagePayload.content) {
          this.addMessage({
            id: `msg-${Date.now()}`,
            from: "sky",
            message: messagePayload.content,
            timestamp: Date.now(),
          });
        }
        break;
    }

    this.state.lastEventTimestamp = timestamp;
    this.notifyStateUpdate();
  }

  /**
   * Add a new message to the chat
   */
  addMessage(message: ChatMessage) {
    this.debug("Adding message", message);
    this.state.messages = [...this.state.messages, message];
    this.notifyStateUpdate();
  }

  /**
   * Add a user message and query
   */
  addUserMessage(query: string) {
    this.debug("Adding user message", { query });
    this.addMessage({
      id: `user-${Date.now()}`,
      from: "user",
      message: query,
      timestamp: Date.now(),
    });
  }

  /**
   * Update current plan
   */
  updatePlan(plan: Plan | null) {
    this.debug("Updating plan", plan);
    this.state.currentPlan = plan;
    this.notifyStateUpdate();
  }

  /**
   * Clear chat history
   */
  clearChat() {
    this.debug("Clearing chat history");
    this.state = this.getInitialState();
    this.notifyStateUpdate();
  }

  /**
   * Update state and notify listeners
   */
  private updateState(update: Partial<ChatState>) {
    this.state = {
      ...this.state,
      ...update,
    };
  }

  /**
   * Notify all state update callbacks
   */
  private notifyStateUpdate() {
    const state = this.getState();
    this.stateUpdateCallbacks.forEach((callback) => callback(state));
  }

  /**
   * Log debug messages
   */
  private debug(message: string, data?: any) {
    if (this.debugCallback) {
      this.debugCallback(`[ChatStateManager] ${message}`, data);
    }
  }

  /**
   * Clean up state manager
   */
  cleanup() {
    this.debug("Cleaning up state manager");
    this.stateUpdateCallbacks = [];
    this.state = this.getInitialState();
  }
}

export const chatStateManager = new ChatStateManager();
