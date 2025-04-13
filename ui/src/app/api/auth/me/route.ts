import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET() {
  try {
    // Get authentication headers including Bearer token if available
    const headers = await getAuthHeaders();

    // Make the API call to fetch user data
    const response = await fetch(`${process.env.API_URL}/auth/me`, {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[Me API] Error fetching user data:",
        response.status,
        errorText
      );
      return NextResponse.json(
        { status: "error", error: "Failed to fetch user data" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Me API] Error in me route:", error);
    return NextResponse.json(
      { status: "error", error: "Failed to fetch user data" },
      { status: 500 }
    );
  }
}
