import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    // Get authentication headers including Bearer token if available
    const headers = await getAuthHeaders();

    // Make the API call to fetch conversation details
    const response = await fetch(
      `${process.env.API_URL}/chat/conversations/${params.id}`,
      {
        method: "GET",
        headers,
        cache: "no-store",
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[Conversation API] Error fetching conversation:",
        response.status,
        errorText
      );
      return NextResponse.json(
        { status: "error", error: "Failed to fetch conversation details" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error("[Conversation API] Error in conversation route:", error);
    return NextResponse.json(
      { status: "error", error: "Failed to fetch conversation details" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    // Get authentication headers
    const headers = await getAuthHeaders();

    // Get the request body
    const body = await request.json();
    // Make the API call to update conversation messages
    const response = await fetch(
      `${process.env.API_URL}/chat/conversations/${params.id}/messages`,
      {
        method: "PATCH",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[Conversation API] Error updating conversation messages:",
        response.status,
        errorText
      );
      return NextResponse.json(
        { status: "error", error: "Failed to update conversation messages" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error(
      "[Conversation API] Error updating conversation messages:",
      error
    );
    return NextResponse.json(
      { status: "error", error: "Failed to update conversation messages" },
      { status: 500 }
    );
  }
}
