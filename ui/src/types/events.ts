export interface ToolExecutingEvent {
  type: "tool.executing";
  call_id: string;
  tool: string;
  title: string;
  args: Record<string, any>;
  run_id: string;
  timestamp: number;
}

export interface ToolResultEvent {
  type: "tool.result";
  call_id: string;
  tool: string;
  title: string;
  result: Array<{
    type: string;
    text?: string;
    annotations?: any;
  }>;
  run_id: string;
  timestamp: number;
}

export interface ToolAwaitingApprovalEvent {
  type: "tool.awaiting_approval";
  run_id: string;
  call_id: string;
  tool: string;
  title: string;
  args: Record<string, any>;
  context: Record<string, any>;
  timestamp: number;
}

export interface ToolDeniedEvent {
  type: "tool.denied";
  call_id: string;
  tool: string;
  title: string;
  args: Record<string, any>;
  run_id: string;
  timestamp: number;
}

export interface ToolApprovedEvent {
  type: "tool.approved";
  call_id: string;
  tool: string;
  title: string;
  args: Record<string, any>;
  run_id: string;
  timestamp: number;
}

export interface ToolErrorEvent {
  type: "tool.error";
  call_id: string;
  tool: string;
  title: string;
  error: string;
  run_id: string;
  timestamp: number;
}

export interface ToolsPendingEvent {
  type: "tools.pending";
  run_id: string;
  tools: Array<{
    call_id: string;
    tool: string;
    title: string;
    args: Record<string, any>;
    requires_approval?: boolean;
    timestamp: number;
  }>;
}

export interface TokenEvent {
  type: "token";
  text: string;
  conversation_id: string;
}

export interface TokenUsageEvent {
  type: "token.usage";
  source: "turn_check" | "main";
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_tokens?: number;
  conversation_id: string;
  timestamp: number;
}

export interface TTFTEvent {
  type: "ttft";
  duration: number;
  timestamp: number;
  run_id: string;
}

export interface ReadyEvent {
  type: "ready";
  run_id: string;
}

export interface HeartbeatEvent {
  type: "heartbeat";
  timestamp: string;
}

export interface ErrorEvent {
  type: "error";
  error: string;
}

export interface CompletedEvent {
  type: "completed";
  status: "completed" | "error";
  run_id?: string;
}

export interface WorkflowCompleteEvent {
  type: "workflow_complete";
  run_id: string;
  result?: any;
  status: "completed" | "awaiting_approval" | "stopped";
}

export interface WorkflowErrorEvent {
  type: "workflow.error";
  run_id: string;
  error: string;
}

export type Event =
  | ToolExecutingEvent
  | ToolResultEvent
  | ToolAwaitingApprovalEvent
  | ToolDeniedEvent
  | ToolApprovedEvent
  | ToolErrorEvent
  | ToolsPendingEvent
  | TokenEvent
  | TokenUsageEvent
  | TTFTEvent
  | ReadyEvent
  | HeartbeatEvent
  | ErrorEvent
  | CompletedEvent
  | WorkflowCompleteEvent
  | WorkflowErrorEvent;
