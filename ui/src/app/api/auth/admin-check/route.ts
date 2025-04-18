import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET() {
  try {
    // Get authentication headers including Bearer token if available
    const headers = await getAuthHeaders();

    // Make the API call to check admin status with explicit IPv4
    const apiUrl =
      process.env.API_URL?.replace("localhost", "127.0.0.1") ||
      "http://127.0.0.1:8080/api/v1";
    const response = await fetch(`${apiUrl}/auth/is_admin_user`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[Admin Check API] Error checking admin status:",
        response.status,
        errorText
      );
      return NextResponse.json(
        { status: "error", error: "Failed to check admin status" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Admin Check API] Error in admin check route:", error);
    return NextResponse.json(
      { status: "error", error: "Failed to check admin status" },
      { status: 500 }
    );
  }
}
