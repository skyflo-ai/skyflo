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
  options:
    | number
    | {
        lastNDays?: number;
        startDate?: Date;
        endDate?: Date;
        startDateTime?: Date;
        endDateTime?: Date;
      } = 30
): Promise<MetricsAggregation> => {
  let queryParams = "";

  if (typeof options === "number") {
    queryParams = `last_n_days=${options}`;
  } else {
    const params = new URLSearchParams();
    params.set("last_n_days", String(options.lastNDays ?? 30));
    if (options.startDate)
      params.set("start_date", options.startDate.toISOString().split("T")[0]);
    if (options.endDate)
      params.set("end_date", options.endDate.toISOString().split("T")[0]);
    if (options.startDateTime)
      params.set("start_datetime", options.startDateTime.toISOString());
    if (options.endDateTime)
      params.set("end_datetime", options.endDateTime.toISOString());
    queryParams = params.toString();
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
};
