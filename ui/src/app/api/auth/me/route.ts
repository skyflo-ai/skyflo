import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET() {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${process.env.API_URL}/auth/me`, {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to fetch user data" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to fetch user data" },
      { status: 500 }
    );
  }
}
