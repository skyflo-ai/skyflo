export interface ToolExecution {
  call_id: string;
  tool: string;
  title: string;
  args: Record<string, any>;
  status:
    | "executing"
    | "completed"
    | "error"
    | "pending"
    | "awaiting_approval"
    | "denied"
    | "approved";
  result?: Array<{
    type: string;
    text?: string;
    annotations?: any;
  }>;
  timestamp: number;
  error?: string;
  requires_approval?: boolean;
}

export type MessageSegment =
  | {
      kind: "text";
      id: string;
      text: string;
      timestamp?: number;
    }
  | {
      kind: "tool";
      id: string;
      toolExecution: ToolExecution;
      timestamp?: number;
    };

export interface ChatMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  segments?: MessageSegment[];
}

export interface ChatState {
  messages: ChatMessage[];
  currentMessage: ChatMessage | null;
  toolExecutions: ToolExecution[];
  isStreaming: boolean;
  isConnected: boolean;
  error: string | null;
  currentRunId: string | null;
}

export interface ChatInterfaceProps {
  conversationId: string;
  initialMessage?: string;
}

export interface ChatMessagesProps {
  messages: ChatMessage[];
  currentMessage?: ChatMessage | null;
  toolExecutions: ToolExecution[];
  isStreaming: boolean;
}

export interface ToolVisualizationProps {
  toolExecution: ToolExecution;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export interface ChatInputProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSubmit: (e?: React.FormEvent) => void;
  handleNewChat: () => void;
  isStreaming: boolean;
  hasMessages?: boolean;
  onCancel?: () => void;
}

export interface Suggestion {
  text: string;
  category: string;
  icon: React.ComponentType<any>;
}
