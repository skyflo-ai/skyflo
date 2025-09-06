import { getAuthHeaders } from "@/lib/api";

export interface ApprovalDecision {
  approve: boolean;
  reason?: string;
  conversation_id?: string;
}

export interface ApprovalResponse {
  status: string;
  call_id: string;
  approved: boolean;
  reason?: string;
}

export interface StopResponse {
  status: string;
  conversation_id: string;
}

const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL;
};

const getClientAuthHeaders = async (): Promise<Record<string, string>> => {
  return {
    "Content-Type": "application/json",
    ...(await getAuthHeaders()),
  };
};

export const approveToolCall = async (
  callId: string,
  reason?: string,
  conversationId?: string
): Promise<ApprovalResponse> => {
  const response = await fetch(`${getApiBaseUrl()}/agent/approvals/${callId}`, {
    method: "POST",
    headers: await getClientAuthHeaders(),
    credentials: "include",
    body: JSON.stringify({
      approve: true,
      reason,
      conversation_id: conversationId,
    } satisfies ApprovalDecision),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Error approving tool call: ${response.statusText} - ${errorText}`
    );
  }

  return await response.json();
};

export const denyToolCall = async (
  callId: string,
  reason?: string,
  conversationId?: string
): Promise<ApprovalResponse> => {
  const response = await fetch(`${getApiBaseUrl()}/agent/approvals/${callId}`, {
    method: "POST",
    headers: await getClientAuthHeaders(),
    credentials: "include",
    body: JSON.stringify({
      approve: false,
      reason,
      conversation_id: conversationId,
    } satisfies ApprovalDecision),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Error denying tool call: ${response.statusText} - ${errorText}`
    );
  }

  return await response.json();
};

export const stopConversation = async (
  conversationId: string,
  runId: string
): Promise<StopResponse> => {
  const body = {
    conversation_id: conversationId,
    run_id: runId,
  };

  const response = await fetch(`${getApiBaseUrl()}/agent/stop`, {
    method: "POST",
    headers: await getClientAuthHeaders(),
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Error stopping conversation: ${response.statusText} - ${errorText}`
    );
  }

  return await response.json();
};
