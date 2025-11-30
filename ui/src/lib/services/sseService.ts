import { getAuthHeaders } from "@/lib/api";
import {
  Event,
  ReadyEvent,
  CompletedEvent,
  WorkflowCompleteEvent,
  TokenUsageEvent,
  TTFTEvent,
} from "@/types/events";
import { ChatMessage, ToolExecution, TokenUsage } from "@/types/chat";

export interface ChatServiceCallbacks {
  onMessage?: (message: ChatMessage) => void;
  onToolExecuting?: (execution: ToolExecution) => void;
  onToolResult?: (execution: ToolExecution) => void;
  onToolsPending?: (executions: ToolExecution[]) => void;
  onToolAwaitingApproval?: (execution: ToolExecution) => void;
  onToolApproved?: (execution: ToolExecution) => void;
  onToolDenied?: (execution: ToolExecution) => void;
  onToolError?: (execution: ToolExecution) => void;
  onToolProgress?: (
    execution: ToolExecution,
    message?: string,
    progress?: number
  ) => void;
  onToken?: (token: string, conversationId: string) => void;
  onTokenUsage?: (usage: TokenUsage, source: "turn_check" | "main") => void;
  onTTFT?: (duration: number, runId: string) => void;
  onError?: (error: string) => void;
  onComplete?: () => void;
  onReady?: (runId: string) => void;
}

export class ChatService {
  private eventSource: EventSource | null = null;
  private callbacks: ChatServiceCallbacks = {};
  private isConnected: boolean = false;
  private toolExecutions = new Map<string, ToolExecution>();
  private hasCompleted: boolean = false;

  constructor(callbacks: ChatServiceCallbacks = {}) {
    this.callbacks = callbacks;
  }

  async startStream(
    messages: ChatMessage[],
    conversationId: string
  ): Promise<void> {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL + "/agent/chat";

    try {
      this.toolExecutions.clear();
      this.hasCompleted = false;

      this.disconnect();

      const requestBody: any = {
        conversation_id: conversationId,
        messages: messages.map((msg) => ({
          role: msg.type === "user" ? "user" : "assistant",
          content: msg.content,
        })),
      };

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
          ...(await this.getAuthHeaders()),
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP ${response.status}: ${response.statusText} - ${errorText}`
        );
      }

      if (!response.body) {
        throw new Error("No response body available");
      }

      this.parseSSEStream(response.body);
      this.isConnected = true;
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        if (error.message.includes("Failed to fetch")) {
          errorMessage = `Cannot connect to backend at ${apiUrl}. Please ensure:\n1. Backend is running on port 8080\n2. CORS is configured\n3. Network connectivity is available`;
        } else if (error.message.includes("404")) {
          errorMessage = `Endpoint not found. Please verify the /agent/chat endpoint exists on your backend`;
        } else if (error.message.includes("500")) {
          errorMessage = `Backend server error. Check backend logs for details`;
        } else {
          errorMessage = error.message;
        }
      }

      this.callbacks.onError?.(errorMessage);
    }
  }

  async startApprovalStream(
    callId: string,
    approve: boolean,
    reason?: string,
    conversationId?: string
  ): Promise<void> {
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL + `/agent/approvals/${callId}`;

    try {
      this.hasCompleted = false;

      this.disconnect();

      const requestBody: any = {
        approve,
        reason,
        conversation_id: conversationId,
      };

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
          ...(await this.getAuthHeaders()),
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP ${response.status}: ${response.statusText} - ${errorText}`
        );
      }

      if (!response.body) {
        throw new Error("No response body available from approval endpoint");
      }

      this.parseSSEStream(response.body);
      this.isConnected = true;
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        if (error.message.includes("Failed to fetch")) {
          errorMessage = `Cannot connect to backend at ${apiUrl}. Please ensure:\n1. Backend is running on port 8080\n2. CORS is configured\n3. Network connectivity is available`;
        } else if (error.message.includes("404")) {
          errorMessage = `Approval endpoint not found. Please verify the /approvals/${callId} endpoint exists on your backend`;
        } else if (error.message.includes("500")) {
          errorMessage = `Backend server error. Check backend logs for details`;
        } else {
          errorMessage = error.message;
        }
      }

      this.callbacks.onError?.(errorMessage);
    }
  }

  private async parseSSEStream(
    body: ReadableStream<Uint8Array>
  ): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          this.processSSELine(line);
        }
      }
    } catch (error) {
      this.callbacks.onError?.(
        error instanceof Error ? error.message : "Stream error"
      );
    } finally {
      reader.releaseLock();
      this.isConnected = false;
    }
  }

  private processSSELine(line: string): void {
    if (line.startsWith("event: ")) {
      return;
    }

    if (line.startsWith("data: ")) {
      const jsonData = line.substring(6);

      if (jsonData.trim() === "") return;

      try {
        const eventData = JSON.parse(jsonData);

        if (eventData.type) {
          this.handleSSEEvent(eventData as Event);
        } else if (eventData.run_id && !eventData.type) {
          const readyEvent: ReadyEvent = {
            type: "ready",
            run_id: eventData.run_id,
          };
          this.handleSSEEvent(readyEvent);
        } else if (eventData.status === "completed" && eventData.result) {
          const workflowCompleteEvent: WorkflowCompleteEvent = {
            type: "workflow_complete",
            run_id: eventData.run_id,
            result: eventData.result,
            status: "completed",
          };
          this.handleSSEEvent(workflowCompleteEvent);
        } else if (eventData.status === "completed") {
          const completedEvent: CompletedEvent = {
            type: "completed",
            status: "completed",
            run_id: eventData.run_id,
          };
          this.handleSSEEvent(completedEvent);
        } else if (eventData.status === "awaiting_approval") {
          const workflowCompleteEvent: WorkflowCompleteEvent = {
            type: "workflow_complete",
            run_id: eventData.run_id,
            result: eventData.result,
            status: "awaiting_approval",
          };
          this.handleSSEEvent(workflowCompleteEvent);
        }
      } catch (error) {}
    }
  }

  private handleSSEEvent(event: Event): void {
    switch (event.type) {
      case "ready":
        this.callbacks.onReady?.(event.run_id);
        break;

      case "tool.executing":
        const executingTool: ToolExecution = {
          call_id: event.call_id,
          tool: event.tool,
          title: event.title,
          args: event.args,
          status: "executing",
          timestamp: event.timestamp,
        };
        this.toolExecutions.set(event.call_id, executingTool);
        this.callbacks.onToolExecuting?.(executingTool);
        break;

      case "tool.result":
        const existingExecution = this.toolExecutions.get(event.call_id);
        if (existingExecution) {
          const completedTool: ToolExecution = {
            ...existingExecution,
            status: "completed",
            result: event.result,
          };
          this.toolExecutions.set(event.call_id, completedTool);
          this.callbacks.onToolResult?.(completedTool);
        }
        break;

      case "tool.awaiting_approval":
        const awaitingApprovalTool: ToolExecution = {
          call_id: event.call_id,
          tool: event.tool,
          title: event.title,
          args: event.args,
          status: "awaiting_approval",
          timestamp: event.timestamp,
          requires_approval: true,
        };
        this.toolExecutions.set(event.call_id, awaitingApprovalTool);
        this.callbacks.onToolAwaitingApproval?.(awaitingApprovalTool);
        break;

      case "tool.approved":
        const approvedExecution = this.toolExecutions.get(event.call_id);
        if (approvedExecution) {
          const approvedTool: ToolExecution = {
            ...approvedExecution,
            status: "approved",
          };
          this.toolExecutions.set(event.call_id, approvedTool);
          this.callbacks.onToolApproved?.(approvedTool);
        } else {
          const approvedTool: ToolExecution = {
            call_id: event.call_id,
            tool: event.tool,
            title: event.title,
            args: event.args,
            status: "approved",
            timestamp: event.timestamp,
          };
          this.toolExecutions.set(event.call_id, approvedTool);
          this.callbacks.onToolApproved?.(approvedTool);
        }
        break;

      case "tool.denied":
        const deniedExecution = this.toolExecutions.get(event.call_id);
        if (deniedExecution) {
          const deniedTool: ToolExecution = {
            ...deniedExecution,
            status: "denied",
          };
          this.toolExecutions.set(event.call_id, deniedTool);
          this.callbacks.onToolDenied?.(deniedTool);
        } else {
          const deniedTool: ToolExecution = {
            call_id: event.call_id,
            tool: event.tool,
            title: event.title,
            args: event.args,
            status: "denied",
            timestamp: event.timestamp,
          };
          this.toolExecutions.set(event.call_id, deniedTool);
          this.callbacks.onToolDenied?.(deniedTool);
        }
        break;

      case "tool.error":
        const errorExecution = this.toolExecutions.get(event.call_id);
        if (errorExecution) {
          const errorTool: ToolExecution = {
            ...errorExecution,
            status: "error",
            error: event.error,
          };
          this.toolExecutions.set(event.call_id, errorTool);
          this.callbacks.onToolError?.(errorTool);
        } else {
          const newErrorTool: ToolExecution = {
            call_id: event.call_id,
            tool: event.tool,
            title: event.title,
            args: {},
            status: "error",
            timestamp: event.timestamp,
            error: event.error,
          };
          this.toolExecutions.set(event.call_id, newErrorTool);
          this.callbacks.onToolError?.(newErrorTool);
        }
        break;

      case "tools.pending":
        const pendingList: ToolExecution[] = [];

        for (const t of event.tools || []) {
          const exec: ToolExecution = {
            call_id: t.call_id,
            tool: t.tool,
            title: t.title,
            args: t.args || {},
            status: "pending",
            timestamp: t.timestamp,
            requires_approval: t.requires_approval,
          };
          this.toolExecutions.set(t.call_id, exec);
          pendingList.push(exec);
        }
        if (pendingList.length > 0) {
          this.callbacks.onToolsPending?.(pendingList);
        }
        break;

      case "token":
        if (this.hasCompleted) {
          return;
        }
        this.callbacks.onToken?.(event.text, event.conversation_id);
        break;

      case "token.usage": {
        const usageEvent = event as TokenUsageEvent;
        this.callbacks.onTokenUsage?.(
          {
            prompt_tokens: usageEvent.prompt_tokens,
            completion_tokens: usageEvent.completion_tokens,
            total_tokens: usageEvent.total_tokens,
            cached_tokens: usageEvent.cached_tokens ?? 0,
          },
          usageEvent.source
        );
        break;
      }

      case "ttft": {
        const ttftEvent = event as TTFTEvent;
        this.callbacks.onTTFT?.(ttftEvent.duration, ttftEvent.run_id);
        break;
      }

      case "error":
        this.callbacks.onError?.(event.error);
        break;

      case "workflow.error":
        this.callbacks.onError?.(event.error);
        break;

      case "completed":
        if (!this.hasCompleted) {
          this.hasCompleted = true;
          this.callbacks.onComplete?.();
        }
        break;

      case "workflow_complete":
        if (!this.hasCompleted) {
          this.hasCompleted = true;
          this.callbacks.onComplete?.();
        }
        break;

      case "heartbeat":
        break;

      default:
        break;
    }
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      return await getAuthHeaders();
    } catch (error) {
      return {};
    }
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnected = false;
    this.hasCompleted = false;
  }

  isConnectedToStream(): boolean {
    return this.isConnected;
  }

  getToolExecutions(): ToolExecution[] {
    return Array.from(this.toolExecutions.values());
  }

  getToolExecution(callId: string): ToolExecution | undefined {
    return this.toolExecutions.get(callId);
  }
}
