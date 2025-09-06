import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET() {
  try {
    const headers = await getAuthHeaders();

    const apiUrl = process.env.API_URL;
    const response = await fetch(`${apiUrl}/auth/is_admin_user`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to check admin status" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to check admin status" },
      { status: 500 }
    );
  }
}
