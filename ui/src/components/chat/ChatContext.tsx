import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
} from "react";
import { Socket } from "socket.io-client";
import {
  AgentState,
  AgentType,
  AgentUpdate,
  MessageData,
  Plan,
  ActionTimer,
} from "./types";

interface ChatState {
  messages: MessageData[];
  isLoading: boolean;
  currentPlan: Plan | null;
  currentStep: string | null;
  actionTimers: ActionTimer[];
  socket: Socket | null;
  error: string | null;
}

type ChatAction =
  | { type: "SET_MESSAGES"; payload: MessageData[] }
  | { type: "ADD_MESSAGE"; payload: MessageData }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_PLAN"; payload: Plan | null }
  | { type: "SET_CURRENT_STEP"; payload: string | null }
  | { type: "UPDATE_ACTION_TIMER"; payload: ActionTimer }
  | { type: "SET_SOCKET"; payload: Socket | null }
  | { type: "SET_ERROR"; payload: string | null };

const initialState: ChatState = {
  messages: [],
  isLoading: false,
  currentPlan: null,
  currentStep: null,
  actionTimers: [],
  socket: null,
  error: null,
};

const ChatContext = createContext<
  | {
      state: ChatState;
      dispatch: React.Dispatch<ChatAction>;
      updateAgentPhase: (agentType: AgentType, message: string) => void;
      handleAgentUpdate: (data: AgentUpdate) => void;
      reconnectWebSocket: (conversationId: string) => Promise<void>;
    }
  | undefined
>(undefined);

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "SET_MESSAGES":
      return { ...state, messages: action.payload };
    case "ADD_MESSAGE":
      return { ...state, messages: [...state.messages, action.payload] };
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "SET_PLAN":
      return { ...state, currentPlan: action.payload };
    case "SET_CURRENT_STEP":
      return { ...state, currentStep: action.payload };
    case "UPDATE_ACTION_TIMER":
      const existingTimerIndex = state.actionTimers.findIndex(
        (timer) => timer.title === action.payload.title
      );
      const newTimers =
        existingTimerIndex >= 0
          ? state.actionTimers.map((timer, index) =>
              index === existingTimerIndex ? action.payload : timer
            )
          : [...state.actionTimers, action.payload];
      return { ...state, actionTimers: newTimers };
    case "SET_SOCKET":
      return { ...state, socket: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload };
    default:
      return state;
  }
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const updateAgentPhase = useCallback(
    (agentType: AgentType, message: string) => {
      const now = Date.now();
      dispatch({
        type: "UPDATE_ACTION_TIMER",
        payload: {
          title: message,
          description: message,
          startTime: now,
          elapsedTime: 0,
          isCompleted: false,
          agentType,
          state: AgentState.EXECUTING,
        },
      });
    },
    []
  );

  const handleAgentUpdate = useCallback((data: AgentUpdate) => {
    if (data.title && data.agent_type) {
      dispatch({
        type: "UPDATE_ACTION_TIMER",
        payload: {
          title: data.title,
          description: data.description || "",
          startTime: Date.now(),
          elapsedTime: 0,
          isCompleted: data.last_step || false,
          agentType: data.agent_type as AgentType,
          state: data.last_step ? AgentState.COMPLETED : AgentState.EXECUTING,
        },
      });
    }

    if (data.answer) {
      dispatch({
        type: "ADD_MESSAGE",
        payload: {
          type: "agent",
          data: {
            role: "assistant",
            content: data.answer,
            created_at: new Date().toISOString(),
          },
        },
      });
    }
  }, []);

  const reconnectWebSocket = useCallback(async (conversationId: string) => {
    // Implementation will be added when we create the WebSocket service
    console.log("Reconnecting WebSocket for conversation:", conversationId);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        state,
        dispatch,
        updateAgentPhase,
        handleAgentUpdate,
        reconnectWebSocket,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
