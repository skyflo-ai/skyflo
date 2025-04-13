"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { queryAgent, createConversation } from "@/lib/api";
import {
  AgentState,
  AgentUpdate,
  Plan,
  TerminalCommand,
  ExecutionStep,
  ValidationCriterion,
  WorkflowMetadata,
} from "./chat/types";
import { useWebSocket } from "@/components/WebSocketProvider";
import ChatMessages from "./chat/components/ChatMessages";
import ChatInput from "./chat/components/ChatInput";
import {
  fetchConversationDetails as fetchConversationService,
  finalizeConversationMessages as finalizeConversationService,
} from "@/lib/services/conversation";
import { showApprovalRequired } from "@/lib/toast";

const CONNECTION_CHECK_INTERVAL = 15000;
const MESSAGE_TIMEOUT = 60000;

export function ChatInterface({
  conversationId: propConversationId,
  initialMessage,
}: {
  conversationId: string;
  initialMessage?: string;
}) {
  const [userMessages, setUserMessages] = useState<any[]>([]);
  const [loadingStatusMessage, setLoadingStatusMessage] = useState<string>();
  const [inputValue, setInputValue] = useState("");
  const [isAgentResponding, setIsAgentResponding] = useState(false);
  const [isResponseGenerating, setIsResponseGenerating] = useState(false);
  const [currentAgentState, setCurrentAgentState] = useState<AgentState>(
    AgentState.IDLE
  );
  const [conversationId, setConversationId] =
    useState<string>(propConversationId);
  const [currentProgress, setCurrentProgress] = useState<number>(0);
  const [currentPhase, setCurrentPhase] = useState<string>("");
  const [terminalOutputs, setTerminalOutputs] = useState<TerminalCommand[]>([]);
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [validationResults, setValidationResults] = useState<
    ValidationCriterion[]
  >([]);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [messageWorkflows, setMessageWorkflows] = useState<
    Record<number, WorkflowMetadata>
  >({});
  const [finalResponse, setFinalResponse] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const initialMessageProcessedRef = useRef(false);

  const addMessage = useCallback((newMessage) => {
    setUserMessages((prev) => [...prev, newMessage]);
  }, []);

  const fetchConversationDetails = useCallback(
    async (id: string) => {
      try {
        setIsLoadingConversation(true);

        const result = await fetchConversationService(id);

        if (result) {
          setUserMessages(result.userMessages);
          setMessageWorkflows(result.messageWorkflows);
          setCurrentAgentState(result.currentAgentState);
          setCurrentProgress(result.currentProgress);
          setCurrentPhase(result.currentPhase);
          setCurrentPlan(result.currentPlan);
          setExecutionSteps(result.executionSteps);
          setValidationResults(result.validationResults);
          setTerminalOutputs(result.terminalOutputs);
          setFinalResponse(result.finalResponse);
          setIsAgentResponding(result.isAgentResponding);
          setIsResponseGenerating(result.isResponseGenerating);
        } else {
          console.error("Failed to fetch conversation details");
          addMessage({
            from: "system",
            message: "Failed to load conversation history.",
            timestamp: Date.now(),
          });
        }
      } catch (error) {
        console.error("Error fetching conversation:", error);
        addMessage({
          from: "system",
          message: "Failed to load conversation history.",
          timestamp: Date.now(),
        });
      } finally {
        setIsLoadingConversation(false);
      }
    },
    [
      addMessage,
      setUserMessages,
      setMessageWorkflows,
      setCurrentAgentState,
      setCurrentProgress,
      setCurrentPhase,
      setCurrentPlan,
      setExecutionSteps,
      setValidationResults,
      setTerminalOutputs,
      setFinalResponse,
      setIsAgentResponding,
      setIsResponseGenerating,
    ]
  );

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [
    executionSteps,
    terminalOutputs,
    validationResults,
    userMessages,
    currentAgentState,
    scrollToBottom,
  ]);

  const finalizeConversationMessages = useCallback(async () => {
    const success = await finalizeConversationService(
      conversationId,
      userMessages,
      messageWorkflows,
      finalResponse
    );

    if (!success) {
      console.error("[ChatInterface] Failed to finalize conversation messages");
    }
  }, [userMessages, messageWorkflows, conversationId, finalResponse]);

  useEffect(() => {
    if (currentPhase === "completed") {
      finalizeConversationMessages();
    }
  }, [currentPhase, finalizeConversationMessages]);

  const [connectionRetries, setConnectionRetries] = useState(0);
  const [lastMessageTime, setLastMessageTime] = useState<number>(0);
  const connectionCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const initialConnectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { socket, isConnected, reconnect } = useWebSocket();

  const resetWorkflowState = () => {
    setCurrentPlan(null);
    setTerminalOutputs([]);
    setExecutionSteps([]);
    setValidationResults([]);

    setCurrentProgress(0);
    setCurrentPhase("");
    setCurrentAgentState(AgentState.IDLE);

    setLoadingStatusMessage("");
    setIsResponseGenerating(false);
    setFinalResponse("");

    setIsAgentResponding(false);
  };

  const processMessage = useCallback(
    async (message: string) => {
      resetWorkflowState();

      addMessage({ from: "user", message, timestamp: Date.now() });

      setIsAgentResponding(true);
      setCurrentAgentState(AgentState.PLANNING);
      setCurrentPhase("planning");
      setCurrentProgress(0.1);
      setLoadingStatusMessage("Planning Approach");

      setLastMessageTime(Date.now());

      setConnectionRetries(0);

      const chatHistory = userMessages.map((message) => ({
        role: message.from === "user" ? "user" : "assistant",
        content: message.message,
        timestamp: message.timestamp || Date.now(),
        contextMarker: message.contextMarker || "standard",
        latest: false,
      }));

      chatHistory.push({
        role: "user",
        content: message,
        timestamp: Date.now(),
        contextMarker: "latest-query",
        latest: true,
      });

      const chatHistoryString = JSON.stringify(chatHistory);

      if (conversationId) {
        try {
          await queryAgent(chatHistoryString, "kubernetes", conversationId);
        } catch (error) {
          console.error("[ChatInterface] Error in conversation flow:", error);
          setCurrentAgentState(AgentState.ERROR);
          setCurrentPhase("error");
          setLoadingStatusMessage(
            `Operation failed: ${error.message || "Unknown error"}`
          );
          setIsAgentResponding(false);

          addMessage({
            from: "sky",
            message: `❌ **Error:** Failed to process your request. Please try again.`,
            timestamp: Date.now(),
          });
        }
      } else {
        console.error("[ChatInterface] No conversation ID available");
        setCurrentAgentState(AgentState.ERROR);
        setCurrentPhase("error");
        setLoadingStatusMessage("Failed to initialize conversation ID");
        setIsAgentResponding(false);

        addMessage({
          from: "sky",
          message: `❌ **Error:** Failed to initialize conversation. Please reload the page.`,
          timestamp: Date.now(),
        });
      }
    },
    [
      addMessage,
      conversationId,
      resetWorkflowState,
      setCurrentAgentState,
      setCurrentPhase,
      setCurrentProgress,
      setConnectionRetries,
      setIsAgentResponding,
      setLastMessageTime,
      setLoadingStatusMessage,
      userMessages,
    ]
  );

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!inputValue.trim()) return;

      await processMessage(inputValue);
      setInputValue("");
    },
    [inputValue, processMessage, setInputValue]
  );

  useEffect(() => {
    if (!socket) return;

    if (connectionCheckIntervalRef.current) {
      clearInterval(connectionCheckIntervalRef.current);
    }

    connectionCheckIntervalRef.current = setInterval(() => {
      const now = Date.now();
      if (
        isConnected &&
        lastMessageTime > 0 &&
        now - lastMessageTime > MESSAGE_TIMEOUT
      ) {
        reconnect();
      }
    }, CONNECTION_CHECK_INTERVAL);

    const eventHandlers: {
      event: string;
      handler: (...args: any[]) => void;
    }[] = [];

    const addHandler = (event: string, handler: (...args: any[]) => void) => {
      socket.on(event, handler);
      eventHandlers.push({ event, handler });
    };

    addHandler("connected", (data) => {
      setConnectionRetries(0);

      setCurrentAgentState(
        isAgentResponding ? AgentState.PLANNING : AgentState.IDLE
      );
      setCurrentPhase(isAgentResponding ? "planning" : "");

      if (userMessages.length > 0) {
        setUserMessages((prevMessages) =>
          prevMessages.filter(
            (msg) =>
              !(
                msg.from === "system" &&
                typeof msg.message === "string" &&
                msg.message.includes("Connection lost")
              )
          )
        );
      }

      if (currentAgentState === AgentState.ERROR && currentPhase === "error") {
        addMessage({
          from: "system",
          message: "Connection restored successfully.",
          timestamp: Date.now(),
        });
      }

      setLastMessageTime(Date.now());
    });

    addHandler("disconnect", () => {
      setCurrentAgentState(AgentState.ERROR);
      setCurrentPhase("error");
      setLoadingStatusMessage("Connection lost. Attempting to reconnect...");

      setConnectionRetries((prev) => prev + 1);

      if (userMessages.length > 0) {
        const hasConnectionMessage = userMessages.some(
          (msg) =>
            msg.from === "system" &&
            typeof msg.message === "string" &&
            msg.message.includes("Connection lost")
        );

        if (!hasConnectionMessage) {
          addMessage({
            from: "system",
            message:
              "Connection lost. Attempting to reconnect automatically...",
            timestamp: Date.now(),
          });
        }
      }
    });

    addHandler("pong", () => {
      setLastMessageTime(Date.now());
    });

    addHandler("agent_update", (event) => {
      if (!event) return;

      setLastMessageTime(Date.now());

      handleAgentUpdate(event);
    });

    const pingInterval = setInterval(() => {
      if (socket && isConnected) {
        socket.emit("ping", { timestamp: Date.now() });
      }
    }, 30000);

    return () => {
      eventHandlers.forEach(({ event, handler }) => {
        socket.off(event, handler);
      });

      if (connectionCheckIntervalRef.current) {
        clearInterval(connectionCheckIntervalRef.current);
        connectionCheckIntervalRef.current = null;
      }

      clearInterval(pingInterval);
    };
  }, [
    socket,
    isConnected,
    isAgentResponding,
    userMessages,
    currentAgentState,
    currentPhase,
    addMessage,
    currentPlan,
    lastMessageTime,
    reconnect,
  ]);

  useEffect(() => {
    if (!conversationId || !isConnected || !socket) return;

    if (
      initialMessage &&
      userMessages.length === 0 &&
      !initialMessageProcessedRef.current
    ) {
      initialMessageProcessedRef.current = true;
      // Just add the message to the UI since the query was already sent
      addMessage({
        from: "user",
        message: initialMessage,
        timestamp: Date.now(),
      });
      setIsAgentResponding(true);
    } else if (
      !initialMessage &&
      !initialMessageProcessedRef.current &&
      !userMessages.length
    ) {
      fetchConversationDetails(conversationId);
    }
  }, [
    conversationId,
    isConnected,
    socket,
    initialMessage,
    userMessages.length,
    initialMessageProcessedRef,
    fetchConversationDetails,
    addMessage,
    setIsAgentResponding,
  ]);

  useEffect(() => {
    if (!propConversationId && !conversationId) {
      const newId = crypto.randomUUID();
      setConversationId(newId);
    } else if (propConversationId && propConversationId !== conversationId) {
      setConversationId(propConversationId);
    }
  }, [propConversationId, conversationId]);

  const handleRestartAPIServer = useCallback(() => {
    if (process.env.NODE_ENV !== "development") return;

    reconnect();

    setCurrentAgentState(AgentState.IDLE);
    setCurrentPhase("");
    setIsAgentResponding(false);

    addMessage({
      from: "system",
      message: "Attempting to refresh WebSocket connection...",
      timestamp: Date.now(),
    });
  }, [reconnect, addMessage]);

  const updateWorkflowState = useCallback(
    (messageIndex: number, additionalData: Partial<WorkflowMetadata> = {}) => {
      if (messageIndex >= 0) {
        setMessageWorkflows((prev) => ({
          ...prev,
          [messageIndex]: {
            agentState: currentAgentState,
            progress: currentProgress,
            phase: currentPhase,
            currentPlan: currentPlan,
            executionSteps: executionSteps,
            validationResults: validationResults,
            terminalOutputs: terminalOutputs,
            timestamp: Date.now(),
            ...additionalData,
          },
        }));
      }
    },
    [
      currentAgentState,
      currentProgress,
      currentPhase,
      currentPlan,
      executionSteps,
      validationResults,
      terminalOutputs,
    ]
  );

  const handleAgentUpdate = (data: AgentUpdate) => {
    let state = AgentState.EXECUTING;

    if (data.agent_type) {
      // Already set from data
    } else if (data.state === "plan") {
      state = AgentState.PLANNING;
    } else if (data.state === "execute") {
      state = AgentState.EXECUTING;
    } else if (data.state === "verify") {
      state = AgentState.VERIFYING;
    }

    if (data.type === "planner_analyzing") {
      state = AgentState.PLANNING;
    }

    if (data.type === "discovery_plan_generated" && data.details?.plan) {
      state = AgentState.PLANNING;
      setCurrentPlan(data.details.plan);

      setLoadingStatusMessage(
        `Planning approach with ${
          data.details.plan.steps?.length || 0
        } discovery steps`
      );
    }

    if (data.type === "plan_generated" && data.details?.plan) {
      state = AgentState.PLANNING;

      // Merge the new plan with any existing discovery steps
      setCurrentPlan((prevPlan) => {
        if (!prevPlan) return data.details.plan;

        // Create a new plan object combining both sets of steps
        return {
          ...data.details.plan,
          steps: [
            ...(prevPlan.steps || []),
            ...(data.details.plan.steps || []),
          ],
        };
      });

      setLoadingStatusMessage(
        `Plan created with ${
          data.details.plan.steps?.length || 0
        } execution steps`
      );
    }

    if (data.type === "step_about_to_execute" && data.details) {
      const stepDetails = data.details as {
        step_id: string;
        tool: string;
        action: string;
        parameters: Record<string, any>;
        status: string;
        conversation_id?: string;
        approval_required?: boolean;
      };

      const stepId = stepDetails.step_id;

      if (stepId) {
        const timestamp = Date.now();
        const compositeKey = `${stepId}-${stepDetails.tool}-${stepDetails.action}-${timestamp}`;

        const newStep: ExecutionStep = {
          step_id: compositeKey,
          original_step_id: stepId,
          tool: stepDetails.tool || "unknown",
          action: stepDetails.action || "execute",
          description:
            data.message || `${stepDetails.tool} ${stepDetails.action}`,
          status:
            (stepDetails.status as
              | "pending"
              | "executing"
              | "completed"
              | "failed") || "pending",
          parameters: stepDetails.parameters || {},
          output: "",
          timestamp: timestamp,
          approval_required: Boolean(stepDetails.approval_required),
        };

        setExecutionSteps((prev) => [...prev, newStep]);
        updateWorkflowState(userMessages.length - 1);

        setLoadingStatusMessage(
          `Preparing to execute: ${stepDetails.tool} ${stepDetails.action}`
        );

        if (Boolean(stepDetails.approval_required)) {
          showApprovalRequired(
            "Approval Required",
            `${stepDetails.tool} ${stepDetails.action}`
          );
        }
      }
    }

    if (data.type === "step_update" && data.data) {
      const stepData = data.data as {
        step_id: string;
        tool: string;
        action: string;
        message?: string;
        status?: string;
        parameters?: Record<string, any>;
        timestamp?: number;
        approval_required?: boolean;
      };

      if (stepData.approval_required && stepData.step_id) {
        const existingStepIndex = executionSteps.findIndex(
          (s) =>
            s.step_id === stepData.step_id ||
            s.original_step_id === stepData.step_id
        );

        if (existingStepIndex >= 0) {
          setExecutionSteps((prev) =>
            prev.map((s, idx) =>
              idx === existingStepIndex ? { ...s, approval_required: true } : s
            )
          );
          updateWorkflowState(userMessages.length - 1, {
            executionSteps: executionSteps.map((s) =>
              s.step_id === stepData.step_id ||
              s.original_step_id === stepData.step_id
                ? { ...s, approval_required: true }
                : s
            ),
          });
        } else {
          const newStep: ExecutionStep = {
            step_id: stepData.step_id,
            tool: stepData.tool || "unknown",
            action: stepData.action || "execute",
            description:
              stepData.message || `Approval required for ${stepData.tool}`,
            status:
              (stepData.status as
                | "pending"
                | "executing"
                | "completed"
                | "failed") || "pending",
            parameters: stepData.parameters || {},
            output: "",
            timestamp: stepData.timestamp || Date.now(),
            approval_required: true,
          };

          setExecutionSteps((prev) => [...prev, newStep]);
          updateWorkflowState(userMessages.length - 1);
        }
      }
    }

    if (data.type === "approval_required" && data.details) {
      const stepDetails = data.details as {
        step_id: string;
        tool: string;
        action: string;
        parameters: Record<string, any>;
        status: string;
        conversation_id?: string;
      };

      const stepId = stepDetails.step_id;

      if (stepId) {
        const existingStepIndex = executionSteps.findIndex(
          (s) => s.step_id === stepId || s.original_step_id === stepId
        );

        if (existingStepIndex >= 0) {
          setExecutionSteps((prev) =>
            prev.map((s, idx) =>
              idx === existingStepIndex ? { ...s, approval_required: true } : s
            )
          );
          updateWorkflowState(userMessages.length - 1, {
            executionSteps: executionSteps.map((s) =>
              s.step_id === stepId || s.original_step_id === stepId
                ? { ...s, approval_required: true }
                : s
            ),
          });
        } else {
          const newStep: ExecutionStep = {
            step_id: stepId,
            tool: stepDetails.tool || "unknown",
            action: stepDetails.action || "execute",
            description:
              data.message || `Approval required for ${stepDetails.tool}`,
            status:
              (stepDetails.status as
                | "pending"
                | "executing"
                | "completed"
                | "failed") || "pending",
            parameters: stepDetails.parameters || {},
            output: "",
            timestamp: Date.now(),
            approval_required: true,
          };

          setExecutionSteps((prev) => [...prev, newStep]);
          updateWorkflowState(userMessages.length - 1);
        }
      }
    }

    if (data.type === "step_complete" && data.details) {
      const stepDetails = data.details as any;

      if (stepDetails && typeof stepDetails === "object") {
        let uniqueIdParts = [stepDetails.step_id];

        if (
          stepDetails.parameters?.name &&
          typeof stepDetails.parameters.name === "string" &&
          !stepDetails.parameters.name.includes("{EXTRACTED_FROM_STEP_")
        ) {
          uniqueIdParts.push(stepDetails.parameters.name);
        }

        if (
          stepDetails.tool &&
          ["describe_resource", "get_pod_logs", "get_resources"].includes(
            stepDetails.tool
          )
        ) {
          uniqueIdParts.push(Date.now().toString());
        }

        const uniqueStepId = uniqueIdParts.join("-");

        const step: ExecutionStep = {
          step_id: uniqueStepId,
          original_step_id: stepDetails.step_id || "unknown",
          tool: stepDetails.tool || "unknown",
          action: stepDetails.action || "execute",
          description:
            stepDetails.description ||
            `${stepDetails.tool || ""} ${stepDetails.action || ""}`,
          status: stepDetails.status || "completed",
          parameters: stepDetails.parameters || {},
          output: stepDetails.output || "",
          timestamp: Date.now(),
          approval_required: Boolean(stepDetails.approval_required),
        };

        const existingStepIndex = executionSteps.findIndex(
          (s) =>
            s.step_id === uniqueStepId ||
            (s.original_step_id === stepDetails.step_id &&
              JSON.stringify(s.parameters) ===
                JSON.stringify(stepDetails.parameters) &&
              s.action === step.action)
        );

        if (existingStepIndex >= 0) {
          setExecutionSteps((prev) =>
            prev.map((s, idx) => (idx === existingStepIndex ? step : s))
          );
          updateWorkflowState(userMessages.length - 1, {
            executionSteps: executionSteps.map((s) =>
              s.step_id === uniqueStepId ||
              (s.original_step_id === stepDetails.step_id &&
                JSON.stringify(s.parameters) ===
                  JSON.stringify(stepDetails.parameters) &&
                s.action === step.action)
                ? step
                : s
            ),
          });
        } else {
          setExecutionSteps((prev) => [...prev, step]);
          updateWorkflowState(userMessages.length - 1);
        }

        state = AgentState.EXECUTING;
        setCurrentPhase("executing");

        let statusMessage = `${step.action || "Completed step"}: ${
          step.description || step.tool
        }`;

        if (
          stepDetails.parameters?.name &&
          typeof stepDetails.parameters.name === "string" &&
          !stepDetails.parameters.name.includes("{EXTRACTED_FROM_STEP_")
        ) {
          statusMessage += ` for ${stepDetails.parameters.name}`;
        }

        setLoadingStatusMessage(statusMessage);
      }
    }

    if (data.type === "verification_complete" && data.details) {
      if (data.details?.validation_results) {
        setValidationResults(data.details.validation_results);
      }

      state = AgentState.VERIFYING;
      setCurrentPhase("verifying");
    }

    if (data.type === "response_complete") {
      setIsResponseGenerating(true);
      setCurrentProgress(data.data?.progress || 0.99);
      setCurrentPhase("responding");
      setCurrentAgentState(AgentState.RESPONDING);

      setLoadingStatusMessage("");

      const responseTerminalOutput: TerminalCommand = {
        command: "generate_response",
        output:
          data.details?.output ||
          data.details?.response ||
          data.data?.answer ||
          data.message ||
          "Final response generated",
        stepId: "response-generation",
        timestamp: Date.now(),
      };

      setFinalResponse(responseTerminalOutput.output);

      setTerminalOutputs((prev) => [
        ...prev.filter((output) => output.stepId !== "response-generation"),
        responseTerminalOutput,
      ]);

      const messageIndex = userMessages.length - 1;
      updateWorkflowState(messageIndex, {
        agentState: AgentState.RESPONDING,
        progress: data.data?.progress || 0.99,
        phase: "responding",
        terminalOutputs: [
          ...(messageWorkflows[messageIndex]?.terminalOutputs || []),
          responseTerminalOutput,
        ],
      });

      setTimeout(() => {
        setIsAgentResponding(false);
        setIsResponseGenerating(false);
        setCurrentAgentState(AgentState.COMPLETED);
        setCurrentPhase("completed");
        setCurrentProgress(1.0);
        setLoadingStatusMessage("");

        const finalMsgIndex = userMessages.length - 1;
        if (finalMsgIndex >= 0) {
          updateWorkflowState(finalMsgIndex, {
            agentState: AgentState.COMPLETED,
            progress: 1.0,
            phase: "completed",
            currentPlan: currentPlan,
            executionSteps: executionSteps,
            validationResults: validationResults,
            terminalOutputs: terminalOutputs,
          });
        }
      }, 1500);
    }

    if (state) {
      setCurrentAgentState(state);
    }

    if (data.phase) {
      setCurrentPhase(data.phase);
    }

    if (data.message || data.title) {
      setLoadingStatusMessage(data.message || data.title || "Processing");
    }

    if (data.data?.progress !== undefined) {
      setCurrentProgress(data.data.progress);
    }

    const messageIndex = userMessages.length - 1;
    updateWorkflowState(messageIndex);

    return "success";
  };

  const handleReloadChat = () => {
    setUserMessages([]);
    setInputValue("");
    setLoadingStatusMessage("");

    setCurrentAgentState(AgentState.IDLE);
    setCurrentPhase("");
    setCurrentProgress(0);
    setIsAgentResponding(false);

    setCurrentPlan(null);
    setTerminalOutputs([]);
    setExecutionSteps([]);
    setValidationResults([]);
    setMessageWorkflows({});

    setTimeout(() => {
      const textArea = document.querySelector("textarea");
      if (textArea) {
        textArea.focus();
      }
    }, 100);
  };

  const handleApproveStep = useCallback(
    (stepId: string) => {
      if (!socket || !isConnected || !conversationId) {
        return;
      }

      const step = executionSteps.find((s) => s.step_id === stepId);
      if (!step) {
        console.error(
          "[ChatInterface] Could not find step to approve:",
          stepId
        );
        return;
      }

      const originalStepId = step.original_step_id;

      socket.emit("tool_call_approved", {
        conversation_id: conversationId,
        step_id: originalStepId,
        timestamp: Date.now(),
      });
    },
    [socket, isConnected, conversationId, executionSteps]
  );

  const handleRejectStep = useCallback(
    (stepId: string) => {
      if (!socket || !isConnected || !conversationId) {
        return;
      }

      const step = executionSteps.find((s) => s.step_id === stepId);
      if (!step) {
        console.error("[ChatInterface] Could not find step to reject:", stepId);
        return;
      }

      const originalStepId = step.original_step_id;

      socket.emit("tool_call_rejected", {
        conversation_id: conversationId,
        step_id: originalStepId,
        timestamp: Date.now(),
      });

      addMessage({
        from: "system",
        message: `Step ${step.tool} ${step.action} rejected by user.`,
        timestamp: Date.now(),
      });

      setIsAgentResponding(false);
      setCurrentAgentState(AgentState.IDLE);
      setCurrentPhase("");
      setLoadingStatusMessage("");
    },
    [
      socket,
      isConnected,
      conversationId,
      executionSteps,
      addMessage,
      setCurrentAgentState,
      setCurrentPhase,
      setLoadingStatusMessage,
      setIsAgentResponding,
    ]
  );

  const handleCancelResponse = useCallback(() => {
    if (!socket || !isConnected || !conversationId) {
      return;
    }

    socket.emit("cancel_response", {
      conversation_id: conversationId,
      timestamp: Date.now(),
    });

    addMessage({
      from: "system",
      message: "Response cancelled by user.",
      timestamp: Date.now(),
    });

    setIsAgentResponding(false);
    setCurrentAgentState(AgentState.IDLE);
    setCurrentPhase("");
    setLoadingStatusMessage("");
  }, [socket, isConnected, conversationId, addMessage]);

  return (
    <div className="flex flex-col justify-between h-full w-full">
      <div className="flex-grow overflow-auto px-8 py-4">
        {isLoadingConversation ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center space-y-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <p className="text-slate-400">Loading conversation...</p>
            </div>
          </div>
        ) : (
          <ChatMessages
            userMessages={userMessages}
            messageWorkflows={messageWorkflows}
            loadingStatusMessage={loadingStatusMessage}
            currentProgress={currentProgress}
            currentPhase={currentPhase}
            isResponseGenerating={isResponseGenerating}
            finalResponse={finalResponse}
            onApproveStep={handleApproveStep}
            onRejectStep={handleRejectStep}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {process.env.NODE_ENV === "development" && connectionRetries > 0 && (
        <div className="p-2 bg-amber-900/30 dark:bg-amber-900/40 text-center text-xs border-t border-amber-700/30">
          <span className="font-mono text-amber-200">
            Connection retries: {connectionRetries} - Last message received:{" "}
            {lastMessageTime
              ? new Date(lastMessageTime).toLocaleTimeString()
              : "none"}
          </span>
        </div>
      )}

      <div className="w-full mt-auto">
        <ChatInput
          inputValue={inputValue}
          setInputValue={setInputValue}
          handleSubmit={handleSubmit}
          handleReloadChat={handleReloadChat}
          isAgentResponding={isAgentResponding}
          messagesExist={userMessages.length > 0}
          handleRestartConnection={handleRestartAPIServer}
          handleCancelResponse={handleCancelResponse}
        />
      </div>
    </div>
  );
}
