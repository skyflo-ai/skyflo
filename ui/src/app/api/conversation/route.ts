import { NextRequest, NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET(request: NextRequest) {
  try {
    const headers = await getAuthHeaders();

    const url = new URL(`${process.env.API_URL}/conversations`);
    const limit = request.nextUrl.searchParams.get("limit");
    const cursor = request.nextUrl.searchParams.get("cursor");
    const query = request.nextUrl.searchParams.get("query");
    if (limit) url.searchParams.set("limit", limit);
    if (cursor) url.searchParams.set("cursor", cursor);
    if (query) url.searchParams.set("query", query);

    const response = await fetch(url.toString(), {
      method: "GET",
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to fetch conversation history" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to fetch conversation history" },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const headers = await getAuthHeaders();
    const body = await request.json().catch(() => ({}));

    const resp = await fetch(`${process.env.API_URL}/conversations`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body || {}),
    });

    const data = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch (e) {
    return NextResponse.json(
      { status: "error", error: "Failed to create conversation" },
      { status: 500 }
    );
  }
}
