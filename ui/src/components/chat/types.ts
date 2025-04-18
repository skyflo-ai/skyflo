export enum AgentState {
  IDLE = "idle",
  PLANNING = "planning",
  EXECUTING = "executing",
  VERIFYING = "verifying",
  RESPONDING = "responding",
  COMPLETED = "completed",
  ERROR = "error",
}

export interface ActionTimer {
  title: string;
  description: string;
  startTime: number;
  elapsedTime: number;
  isCompleted: boolean;
  agentType: AgentType;
  state: AgentState;
}

export type AgentType = "planner" | "executor" | "verifier" | "system";

export interface AgentUpdate {
  type: string;
  agent?: string;
  agent_type?: string;
  message?: string;
  phase?: string;
  state?: string;
  title?: string;
  description?: string;
  data?: {
    progress?: number;
    message?: string;
    answer?: string;
    last_step?: boolean;
    timestamp?: number;
    phase?: string;
    conversation_id?: string;
  };
  details?: {
    plan?: Plan;
    response?: string;
    validation_results?: ValidationCriterion[];
    status?: string;
    criterion?: string;
    details?: string;
    response_length?: number;
    timestamp?: string;
    conversation_id?: string;
    output?: string;
  };
  answer?: string;
  conversation_id?: string;
  last_step?: boolean;
}

export interface MessageData {
  type: string;
  data?: {
    role: string;
    content: string;
    id?: string;
    sequence?: number;
    created_at?: string;
    metadata?: Record<string, unknown>;
  };
}

export interface TerminalOutput {
  command: string;
  output: string;
}

export interface PlanStep {
  step_id: string;
  tool: string;
  action: string;
  parameters: Record<string, any>;
  description: string;
  required: boolean;
  recursive: boolean;
  discovery_step: boolean;
  error_handling?: {
    retry_count: number;
    retry_delay: number;
    fallback_action: string;
  };
  status?: "pending" | "executing" | "completed" | "failed";
}

export interface Plan {
  query: string;
  intent: string;
  steps: PlanStep[];
  validation_criteria: string[];
  context: {
    requires_verification: boolean;
    additional_context: string;
    target_namespace: string;
    resource_type: string;
    discovery_context: {
      resource_type: string;
      filters: string;
    };
  };
  plan_id: string;
  status: string;
}

export interface StepUpdate {
  step_id: string;
  status: "pending" | "executing" | "completed" | "failed";
  tool: string;
  action: string;
  parameters?: Record<string, any>;
  output?: any;
  error?: string;
  timestamp?: number;
}

export interface VerificationCriteria {
  criterion: string;
  description?: string;
  importance?: "high" | "medium" | "low";
}

export interface VerificationResult {
  criterion: string;
  criterion_index: number;
  total_criteria: number;
  status: "success" | "failure" | "checking";
  details?: string;
}

export interface TerminalCommand {
  command: string;
  output: string;
  stepId: string;
  timestamp: number;
  tool?: string;
  action?: string;
  status?: string;
  parameters?: any;
}

export interface ValidationCriterion {
  criterion: string;
  status: "success" | "failure" | "warning" | "pending";
  details?: string;
}

export interface ExecutionStep {
  step_id: string;
  original_step_id?: string;
  tool: string;
  action: string;
  description: string;
  status: "pending" | "executing" | "completed" | "failed";
  parameters: Record<string, any>;
  output: string;
  timestamp: number;
  approval_required?: boolean;
}

export interface WorkflowMetadata {
  agentState: AgentState;
  progress: number;
  phase: string;
  currentPlan: Plan | null;
  executionSteps: ExecutionStep[];
  validationResults: ValidationCriterion[];
  terminalOutputs: TerminalCommand[];
  timestamp: number;
  finalResponse?: string;
}

export interface WorkflowStep {
  id: string;
  type: "plan" | "execution" | "verification" | "response";
  status: "pending" | "in_progress" | "success" | "failure";
  title: string;
  description: string;
  details?: any;
  timestamp: number;
  output?: string;
  approval_required?: boolean;
}

export interface WorkflowPhase {
  type: "planning" | "executing" | "verifying" | "responding";
  status: "pending" | "in_progress" | "success" | "failure";
  steps: WorkflowStep[];
  startTime?: number;
  endTime?: number;
}

export interface WorkflowVisualizerProps {
  currentPlan: Plan | null;
  executionSteps: ExecutionStep[];
  validationResults: ValidationCriterion[];
  currentPhase: string;
  currentAgentState: AgentState;
  loadingStatusMessage?: string;
  terminalOutputs: TerminalCommand[];
  finalResponse?: string;
  onApprove?: (stepId: string) => void; // Add approval handler
  onReject?: (stepId: string) => void; // Add reject handler
}

export interface Suggestion {
  text: string;
  category: string;
  icon: React.ComponentType<any>;
}

export interface ChatInterfaceProps {
  conversationId: string;
  initialMessage?: string;
}

export interface ChatSuggestionsProps {
  suggestions: Suggestion[];
  onSuggestionClick: (suggestion: string) => void;
}
