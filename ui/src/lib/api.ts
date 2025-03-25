"use server";

import { cookies } from "next/headers";

// Add detailed logging for better debugging
const logRequest = (endpoint: string, method: string, body?: any) => {
  console.log(`[Skyflo API] ${method} request to ${endpoint}`);
  if (body) {
    console.log(
      `[Skyflo API] Request body: ${JSON.stringify(body).substring(0, 500)}...`
    );
  }
};

const logResponse = (endpoint: string, status: number, data: any) => {
  console.log(`[Skyflo API] Response from ${endpoint}: status ${status}`);
  console.log(
    `[Skyflo API] Response data: ${JSON.stringify(data).substring(0, 500)}...`
  );
};

const logError = (endpoint: string, error: any) => {
  console.error(`[Skyflo API] Error in request to ${endpoint}:`, error);
};

// Change the function to make it exportable
export async function getAuthHeaders() {
  try {
    // Get all cookies first
    const nextCookies = cookies().getAll();
    const cookieHeader = nextCookies
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    // Look for the auth token cookie using various possible names
    const tokenCookie =
      nextCookies.find((cookie) => cookie.name === "auth_token") ||
      nextCookies.find((cookie) => cookie.name === "access_token") ||
      nextCookies.find((cookie) => cookie.name === "token");

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      Cookie: cookieHeader,
    };

    // Add Authorization header if token is found
    if (tokenCookie) {
      headers["Authorization"] = `Bearer ${tokenCookie.value}`;
      console.log(
        "[Skyflo API] Authorization token found and included in headers"
      );
    } else {
      console.log("[Skyflo API] No authorization token found in cookies");
    }

    return headers;
  } catch (error) {
    console.error("[Skyflo API] Error getting auth headers:", error);
    return { "Content-Type": "application/json" };
  }
}

export async function queryAgent(
  query: string,
  agentPath: string | null,
  conversationId?: string,
  clusterId: string = "default"
) {
  const endpoint = `${process.env.API_URL}/chat/query`;
  logRequest(endpoint, "POST", { query, conversationId, clusterId });

  try {
    // Get authentication headers including Bearer token if available
    const headers = await getAuthHeaders();

    // Format query if it looks like a JSON string (for chat history)
    let formattedQuery = query;
    try {
      // Check if the query is a JSON string that represents chat history
      if (query.trim().startsWith("[") && query.includes('"role":')) {
        // It's already a JSON string, use as is
        formattedQuery = query;
        console.log("[Skyflo API] Using chat history format for query");
      }
    } catch (error) {
      // Not a valid JSON, use as regular query
      console.log("[Skyflo API] Using regular format for query");
    }

    // Check if using a temporary conversation ID (for unauthenticated mode)
    const isUsingTempId = conversationId?.startsWith("temp-");

    // If using a temporary ID, return a simulated response instead of making an actual API call
    if (isUsingTempId) {
      console.log(
        `[Skyflo API] Using temporary ID (${conversationId}) - generating simulated response`
      );

      // Create a mock response similar to what the backend would return
      return {
        status: "completed",
        result: {
          query: formattedQuery,
          workflow_id: `temp-workflow-${Date.now()}`,
          start_time: Date.now() / 1000,
          plan: {
            query: formattedQuery,
            intent: "Simulated intent for local processing",
            steps: [
              {
                step_id: "1",
                tool: "local_processing",
                action: "simulate response",
              },
            ],
          },
          conversation_id: conversationId,
        },
        message:
          "This is a simulated response because you're using a temporary conversation ID.",
      };
    }

    const requestBody = {
      query: formattedQuery,
      conversation_id: conversationId,
      cluster_id: clusterId,
      agent_path: agentPath,
    };

    console.log(
      `[Skyflo API] Full request body: ${JSON.stringify(requestBody)}`
    );

    if (!conversationId) {
      console.warn(
        "[Skyflo API] Warning: No conversation ID provided for query. WebSocket events may not be received."
      );
    } else {
      console.log(`[Skyflo API] Using conversation ID: ${conversationId}`);
    }

    const response = await fetch(endpoint, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorMessage = await response.text();
      logError(endpoint, `Status: ${response.status}, Error: ${errorMessage}`);

      // If unauthorized, return a simulated response
      if (response.status === 401) {
        console.warn(
          "[Skyflo API] Authentication error - using simulated response"
        );
        return {
          status: "completed",
          result: {
            query: formattedQuery,
            workflow_id: `auth-error-${Date.now()}`,
            start_time: Date.now() / 1000,
            conversation_id: conversationId,
          },
          message: "Authentication required. This is a simulated response.",
        };
      }

      throw new Error(
        `Failed to query agent. Status: ${response.status}, error: ${errorMessage}`
      );
    }

    const data = await response.json();
    logResponse(endpoint, response.status, data);

    // Log the workflow ID and conversation ID for debugging
    if (data && data.result && data.result.workflow_id) {
      console.log(
        `[Skyflo API] Workflow ID: ${data.result.workflow_id}, Conversation ID: ${conversationId}`
      );
    }

    return data;
  } catch (error) {
    logError(endpoint, error);
    // Instead of throwing, return a simulated response
    console.warn(
      "[Skyflo API] Error in queryAgent, returning simulated response"
    );
    return {
      status: "completed",
      result: {
        query: query,
        workflow_id: `error-${Date.now()}`,
        start_time: Date.now() / 1000,
        conversation_id: conversationId || `temp-${Date.now()}`,
      },
      message: "An error occurred. This is a simulated response.",
      error: error.message,
    };
  }
}

export const createConversation = async (
  clientConversationId?: string
): Promise<any> => {
  try {
    console.log(
      `Creating conversation with clientConversationId: ${clientConversationId} on ${process.env.API_URL}`
    );
    const response = await fetch(`${process.env.API_URL}/ws/conversations`, {
      method: "POST",
      headers: {
        ...(await getAuthHeaders()),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        conversation_id: clientConversationId,
        title: `New Conversation ${new Date().toISOString().split("T")[0]}`,
      }),
    });

    console.log(`Response: ${JSON.stringify(response)}`);

    if (!response.ok) {
      throw new Error(`Error creating conversation: ${response.statusText}`);
    }

    const data = await response.json();

    // Add confirmation check with retries
    const maxRetries = 3;
    const baseDelay = 100; // 100ms initial delay

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      // Check if conversation exists
      const checkResponse = await fetch(
        `${process.env.API_URL}/ws/conversations/${data.id}`,
        {
          headers: await getAuthHeaders(),
        }
      );

      if (checkResponse.ok) {
        return data;
      }

      // If not found and we have retries left, wait with exponential backoff
      if (attempt < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }
    }

    // If we get here, conversation wasn't confirmed after all retries
    console.warn(
      `Conversation ${data.id} creation not confirmed after ${maxRetries} attempts`
    );
    return data; // Return anyway since the creation request succeeded
  } catch (error) {
    console.error("Error creating conversation:", error);
    throw error;
  }
};

export async function getConversations() {
  const response = await fetch(`${process.env.API_URL}/ws/conversations`, {
    headers: await getAuthHeaders(),
  });
  return response.json();
}

export async function getWsUrl() {
  try {
    // First try to get the URL from environment variable
    let wsUrl = process.env.NEXT_PUBLIC_API_WS_URL;
    console.log(`[Skyflo API] NEXT_PUBLIC_API_WS_URL: ${wsUrl}`);

    // If not specified in env, derive from API URL
    if (!wsUrl) {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      console.log(`[Skyflo API] Using API_URL: ${apiUrl}`);
      // Convert HTTP to WS protocol
      wsUrl = apiUrl.replace(/^http/, "ws");
      console.log(`[Skyflo API] Derived WebSocket URL from API URL: ${wsUrl}`);
    } else {
      console.log(`[Skyflo API] Using configured WebSocket URL: ${wsUrl}`);
    }

    // If URL doesn't specify protocol, default to secure in production, insecure in dev
    if (!wsUrl.startsWith("ws://") && !wsUrl.startsWith("wss://")) {
      wsUrl =
        process.env.NODE_ENV === "production"
          ? `wss://${wsUrl}`
          : `ws://${wsUrl}`;
      console.log(`[Skyflo API] Added protocol to WebSocket URL: ${wsUrl}`);
    }

    // Remove any path and ensure the URL ends with a trailing slash for Socket.IO
    // Only keep the hostname and port
    const url = new URL(wsUrl);
    const baseUrl = `${url.protocol}//${url.host}/`;
    console.log(`[Skyflo API] Formatted WebSocket URL: ${baseUrl}`);

    return baseUrl;
  } catch (error) {
    console.error("[Skyflo API] Error getting WebSocket URL:", error);
    // Fallback to default
    return process.env.NODE_ENV === "production"
      ? "wss://api.skyflo.ai/"
      : "ws://localhost:8000/";
  }
}
