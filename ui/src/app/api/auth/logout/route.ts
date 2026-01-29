import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function POST() {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${process.env.API_URL}/auth/logout`, {
      method: "POST",
      headers,
      cache: "no-store",
    });

    const data = await response.json().catch(() => null);
    const nextResponse = NextResponse.json(
      data ?? { status: "ok" },
      { status: response.status }
    );

    // Forward set-cookie headers from backend to clear httpOnly cookies
    const setCookies = response.headers.getSetCookie();
    if (setCookies.length > 0) {
      setCookies.forEach((cookie) => {
        nextResponse.headers.append("set-cookie", cookie);
      });
    }

    return nextResponse;
  } catch (error) {
    console.error("Logout error:", error);
    return NextResponse.json(
      { status: "error", error: "Failed to logout" },
      { status: 500 }
    );
  }
}
