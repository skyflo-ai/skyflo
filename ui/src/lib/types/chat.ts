/**
 * Types for the chat interface components and socket events
 */

export enum AgentState {
  IDLE = "idle",
  PLANNING = "planning",
  EXECUTING = "executing",
  VERIFYING = "verifying",
  COMPLETED = "completed",
  ERROR = "error",
}

export interface PlanStep {
  step_id: string;
  tool: string;
  action: string;
  parameters: any;
  description: string;
  required: boolean;
  recursive: boolean;
  discovery_step: boolean;
  error_handling: {
    retry_count: number;
    retry_delay: number;
    fallback_action: string;
  };
  status?: "pending" | "executing" | "completed" | "failed";
  timestamp?: number; // For event ordering
}

export interface Plan {
  id: string; // Unique identifier for the plan
  query: string;
  intent: string;
  steps: PlanStep[];
  validation_criteria: string[];
  context: {
    requires_verification: boolean;
    additional_context: string;
    target_namespace?: string;
    resource_type?: string;
    discovery_context?: {
      resource_type: string;
      filters: string;
    };
  };
  created_at: number; // Timestamp when plan was created
  updated_at: number; // Timestamp of last update
}

export interface ChatMessage {
  id: string;
  from: "user" | "sky";
  message?: string;
  plan?: Plan;
  currentStep?: string;
  stepOutputs?: Record<string, string>;
  timestamp: number;
  error?: string;
}

export interface SocketEvent<T = any> {
  type: string;
  data?: T;
  timestamp: number;
  sequence_number?: number; // For ordering events
}

export interface PlannerStartEvent {
  conversation_id: string;
  query: string;
}

export interface PlannerCompleteEvent {
  conversation_id: string;
  plan: Plan;
}

export interface ExecutorProgressEvent {
  conversation_id: string;
  step_id: string;
  progress: number;
  status: string;
}

export interface StepOutputEvent {
  conversation_id: string;
  step_id: string;
  output: string;
}

export interface StepCompleteEvent {
  conversation_id: string;
  step_id: string;
  output?: string;
}

export interface StepFailedEvent {
  conversation_id: string;
  step_id: string;
  error: string;
  retry_count?: number;
}

export interface PlanFailedEvent {
  conversation_id: string;
  message: string;
  error_code?: string;
}

export interface VerifierStartEvent {
  conversation_id: string;
}

export interface VerifierCompleteEvent {
  conversation_id: string;
  validation_results: {
    success: boolean;
    message: string;
    details?: any;
  };
}

// State management types
export interface ChatState {
  messages: ChatMessage[];
  currentPlan: Plan | null;
  agentState: AgentState;
  currentPhase: string;
  progress: number;
  error: string | null;
  isConnected: boolean;
  lastEventTimestamp: number;
}

export interface ChatStateUpdate {
  type: string;
  payload: Partial<ChatState>;
  timestamp: number;
}
