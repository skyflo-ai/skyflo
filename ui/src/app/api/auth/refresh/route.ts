import { NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function POST() {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${process.env.API_URL}/auth/refresh`, {
      method: "POST",
      headers,
      cache: "no-store",
    });

    const data = await response.json().catch(() => null);
    const nextResponse = NextResponse.json(
      data ?? { status: "error", error: "Failed to refresh session" },
      { status: response.status }
    );

    const setCookies = response.headers.getSetCookie();
    if (setCookies.length > 0) {
      setCookies.forEach((cookie) => {
        nextResponse.headers.append("set-cookie", cookie);
      });
    }

    return nextResponse;
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to refresh session" },
      { status: 500 }
    );
  }
}
