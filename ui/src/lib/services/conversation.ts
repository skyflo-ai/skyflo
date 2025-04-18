import { AgentState } from "@/components/chat/types";
import {
  WorkflowMetadata,
  ValidationCriterion,
  TerminalCommand,
  ExecutionStep,
  Plan,
} from "@/components/chat/types";

interface FetchConversationResult {
  userMessages: any[];
  messageWorkflows: Record<number, WorkflowMetadata>;
  currentAgentState: AgentState;
  currentProgress: number;
  currentPhase: string;
  currentPlan: Plan | null;
  executionSteps: ExecutionStep[];
  validationResults: ValidationCriterion[];
  validationStatus: "success" | "failure" | "partial" | "pending";
  terminalOutputs: TerminalCommand[];
  finalResponse: string;
  isAgentResponding: boolean;
  isResponseGenerating: boolean;
}

/**
 * Fetches conversation details from the API and processes the response
 * @param id - Conversation ID to fetch
 * @returns Processed conversation data with all necessary state values
 */
export async function fetchConversationDetails(
  id: string
): Promise<FetchConversationResult | null> {
  try {
    const response = await fetch(`/api/conversation/${id}`);
    const data = await response.json();

    if (response.ok && data.status === "success" && data.messages) {
      // Add all userMessages from the conversation history
      const conversationMessages = data.messages || [];

      // Initialize workflows object to store metadata
      const loadedWorkflows: Record<number, WorkflowMetadata> = {};
      let lastUserMessageIndex = -1;

      // Process messages and extract workflow metadata
      const processedMessages = conversationMessages
        .map((msg: any, index: number) => {
          if (msg.role === "user") {
            lastUserMessageIndex++;
            return {
              from: "user",
              message: msg.content,
              timestamp: msg.created_at || Date.now(),
            };
          }

          // For 'sky' messages, extract workflow metadata from content if available
          if (msg.role === "sky" && typeof msg.content === "object") {
            // Store the workflow metadata for the last user message
            if (lastUserMessageIndex >= 0) {
              loadedWorkflows[lastUserMessageIndex] = msg.content;
            }
            return null;
          }

          // Regular sky message (non-workflow)
          return {
            from: "sky",
            message: msg.content,
            timestamp: msg.created_at || Date.now(),
          };
        })
        .filter(Boolean); // Remove null entries

      // Find the last workflow state to restore the current UI state
      const lastWorkflow = Object.values(loadedWorkflows).pop();

      // Initialize result object with default values
      const result: FetchConversationResult = {
        userMessages: processedMessages,
        messageWorkflows: loadedWorkflows,
        currentAgentState: AgentState.IDLE,
        currentProgress: 0,
        currentPhase: "",
        currentPlan: null,
        executionSteps: [],
        validationResults: [],
        validationStatus: "pending",
        terminalOutputs: [],
        finalResponse: "",
        isAgentResponding: false,
        isResponseGenerating: false,
      };

      if (lastWorkflow) {
        // Restore the conversation state from the last workflow
        result.currentAgentState =
          lastWorkflow.agentState || AgentState.COMPLETED;
        result.currentProgress = lastWorkflow.progress || 1.0;
        result.currentPhase = lastWorkflow.phase || "completed";
        result.currentPlan = lastWorkflow.currentPlan || null;

        // Restore other UI state
        if (lastWorkflow.executionSteps) {
          result.executionSteps = lastWorkflow.executionSteps;
        }

        if (lastWorkflow.validationResults) {
          result.validationResults = lastWorkflow.validationResults;

          // Determine validation status based on results
          const allSuccess = lastWorkflow.validationResults.every(
            (v) => v.status === "success"
          );
          const anyFailed = lastWorkflow.validationResults.some(
            (v) => v.status === "failure"
          );

          if (allSuccess) {
            result.validationStatus = "success";
          } else if (anyFailed) {
            result.validationStatus = "failure";
          } else {
            result.validationStatus = "partial";
          }
        }

        if (lastWorkflow.terminalOutputs) {
          result.terminalOutputs = lastWorkflow.terminalOutputs;

          // Set final response from terminal outputs if available
          const responseOutput = lastWorkflow.terminalOutputs.find(
            (output) => output.stepId === "response-generation"
          );
          if (responseOutput && responseOutput.output) {
            result.finalResponse = responseOutput.output;
          }
        }

        if (lastWorkflow.finalResponse) {
          result.finalResponse = lastWorkflow.finalResponse;
        }
      }

      return result;
    } else {
      console.error("[ConversationService] Error response:", data);
      return null;
    }
  } catch (error) {
    console.error("[ConversationService] Error fetching conversation:", error);
    return null;
  }
}

/**
 * Finalizes the conversation by updating the messages in the API
 * @param conversationId - The ID of the conversation to update
 * @param userMessages - Array of user messages
 * @param messageWorkflows - Record of workflow metadata for each message
 * @param finalResponse - The final response text
 * @returns True if the update was successful, false otherwise
 */
export async function finalizeConversationMessages(
  conversationId: string,
  userMessages: any[],
  messageWorkflows: Record<number, WorkflowMetadata>,
  finalResponse: string
): Promise<boolean> {
  const formattedMessages = [];

  // Process each user message and its corresponding workflow
  for (let i = 0; i < userMessages.length; i++) {
    // Add user message
    formattedMessages.push({
      role: "user",
      content: userMessages[i].message,
      created_at: userMessages[i].timestamp,
    });

    // If there's a workflow for this message, add it as a sky message
    if (messageWorkflows[i]) {
      formattedMessages.push({
        role: "sky",
        content: {
          finalResponse: finalResponse,
          ...messageWorkflows[i],
        },
        created_at: messageWorkflows[i].timestamp,
      });
    }
  }

  try {
    const response = await fetch(`/api/conversation/${conversationId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: formattedMessages,
      }),
    });

    if (!response.ok) {
      console.error(
        "[ConversationService] Failed to update conversation messages:",
        await response.text()
      );
      return false;
    }
    return true;
  } catch (error) {
    console.error(
      "[ConversationService] Error updating conversation messages:",
      error
    );
    return false;
  }
}
