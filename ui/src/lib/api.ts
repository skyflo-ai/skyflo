"use server";

import { cookies } from "next/headers";
import { MetricsAggregation } from "../types/analytics";

export async function getAuthHeaders() {
  try {
    const nextCookies = cookies().getAll();
    const cookieHeader = nextCookies
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const tokenCookie =
      nextCookies.find((cookie) => cookie.name === "auth_token") ||
      nextCookies.find((cookie) => cookie.name === "access_token") ||
      nextCookies.find((cookie) => cookie.name === "token");

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      Cookie: cookieHeader,
    };

    if (tokenCookie) {
      headers["Authorization"] = `Bearer ${tokenCookie.value}`;
    }

    return headers;
  } catch (error) {
    return { "Content-Type": "application/json" };
  }
}

export const createConversation = async (
  clientConversationId?: string
): Promise<any> => {
  try {
    const response = await fetch(`${process.env.API_URL}/conversations`, {
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

    if (!response.ok) {
      throw new Error(`Error creating conversation: ${response.statusText}`);
    }

    const data = await response.json();

    const maxRetries = 3;
    const baseDelay = 100; // 100ms initial delay

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const checkResponse = await fetch(
        `${process.env.API_URL}/conversations/${data.id}`,
        {
          headers: await getAuthHeaders(),
        }
      );

      if (checkResponse.ok) {
        return data;
      }

      if (attempt < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }
    }

    return data;
  } catch (error) {
    throw error;
  }
};

export const getMetrics = async (
  options: number | { lastNDays?: number; startDate?: Date; endDate?: Date } = 30
): Promise<MetricsAggregation> => {
  try {
    let queryParams = "";

    if (typeof options === "number") {
      queryParams = `last_n_days=${options}`;
    } else {
      const params = [];
      if (options.lastNDays) params.push(`last_n_days=${options.lastNDays}`);
      if (options.startDate) params.push(`start_date=${options.startDate.toISOString().split("T")[0]}`);
      if (options.endDate) params.push(`end_date=${options.endDate.toISOString().split("T")[0]}`);
      queryParams = params.join("&");
    }

    const response = await fetch(
      `${process.env.API_URL}/analytics/metrics?${queryParams}`,
      {
        headers: await getAuthHeaders(),
        cache: "no-store",
      }
    );

    if (!response.ok) {
      throw new Error(`Error fetching metrics: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to fetch metrics:", error);
    throw error;
  }
};
