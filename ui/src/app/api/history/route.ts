import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET() {
  try {
    // Get authentication headers including Bearer token if available
    const headers = await getAuthHeaders();

    // Make the API call to fetch conversations
    const response = await fetch(`${process.env.API_URL}/chat/conversations`, {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[History API] Error fetching conversations:",
        response.status,
        errorText
      );
      return NextResponse.json(
        { status: "error", error: "Failed to fetch conversation history" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error("[History API] Error in history route:", error);
    return NextResponse.json(
      { status: "error", error: "Failed to fetch conversation history" },
      { status: 500 }
    );
  }
}
