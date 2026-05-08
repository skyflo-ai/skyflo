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

export interface ThinkingEvent {
  type: "thinking";
  text: string;
  conversation_id: string;
  run_id: string;
}

export interface ThinkingCompleteEvent {
  type: "thinking.complete";
  content: string;
  duration_ms: number;
  run_id: string;
  timestamp: number;
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
  status: "completed" | "error" | "stopped";
  run_id?: string;
  duration_ms?: number;
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

export interface ConversationTitleGeneratedEvent {
  type: "conversation.title.generated";
  conversation_id: string;
  title: string;
  timestamp: number;
}

export interface MemoryContextLoadedEvent {
  type: "memory.context.loaded";
  run_id: string;
  documents: Array<{
    document_id: string;
    store_slug: string;
    path: string;
    trust_level: string;
    version_id: string | null;
    used_as: string;
  }>;
  timestamp: number;
}

export interface MemorySearchEvent {
  type: "memory.search";
  run_id: string;
  query: string;
  results_count: number;
  timestamp: number;
}

export interface MemoryWriteCreatedEvent {
  type: "memory.write.created";
  run_id: string;
  store_slug: string;
  path: string;
  document_id: string;
  document_type: string;
  timestamp: number;
}

export interface MemoryWriteBlockedEvent {
  type: "memory.write.blocked";
  run_id: string;
  reason: string;
  severity: string;
  timestamp: number;
}

export interface MemoryPolicyDeniedEvent {
  type: "memory.policy.denied";
  run_id: string;
  operation: string;
  store_slug: string;
  reason: string;
  timestamp: number;
}

export interface MemoryPromotionProposedEvent {
  type: "memory.promotion.proposed";
  run_id: string;
  source_document_id: string;
  target_store_slug: string;
  timestamp: number;
}

export interface MemorySafetyFlaggedEvent {
  type: "memory.safety.flagged";
  run_id: string;
  finding_count: number;
  severity: string;
  timestamp: number;
}

export type Event =
  | ToolExecutingEvent
  | ToolResultEvent
  | ToolAwaitingApprovalEvent
  | ToolDeniedEvent
  | ToolApprovedEvent
  | ToolErrorEvent
  | ToolsPendingEvent
  | ThinkingEvent
  | ThinkingCompleteEvent
  | TokenEvent
  | TokenUsageEvent
  | TTFTEvent
  | ReadyEvent
  | HeartbeatEvent
  | ErrorEvent
  | CompletedEvent
  | WorkflowCompleteEvent
  | WorkflowErrorEvent
  | ConversationTitleGeneratedEvent
  | MemoryContextLoadedEvent
  | MemorySearchEvent
  | MemoryWriteCreatedEvent
  | MemoryWriteBlockedEvent
  | MemoryPolicyDeniedEvent
  | MemoryPromotionProposedEvent
  | MemorySafetyFlaggedEvent;
