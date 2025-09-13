import { NextRequest, NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET(request: NextRequest) {
  try {
    const headers = await getAuthHeaders();
    const provider = request.nextUrl.searchParams.get("provider");
    const url = new URL(`${process.env.API_URL}/integrations`);
    if (provider) url.searchParams.set("provider", provider);

    const resp = await fetch(url.toString(), {
      method: "GET",
      headers,
      cache: "no-store",
    });

    const text = await resp.text();
    const body = text ? JSON.parse(text) : {};
    return NextResponse.json(body, { status: resp.status });
  } catch (e) {
    return NextResponse.json(
      { status: "error", error: "Failed to fetch integrations" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const headers = await getAuthHeaders();
    const body = await request.json().catch(() => ({}));

    const resp = await fetch(`${process.env.API_URL}/integrations`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });

    const text = await resp.text();
    const data = text ? JSON.parse(text) : {};
    return NextResponse.json(data, { status: resp.status });
  } catch (e) {
    return NextResponse.json(
      { status: "error", error: "Failed to create integration" },
      { status: 500 }
    );
  }
}
