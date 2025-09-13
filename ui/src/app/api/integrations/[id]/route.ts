import { NextRequest, NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const headers = await getAuthHeaders();
    const body = await request.json().catch(() => ({}));

    const resp = await fetch(
      `${process.env.API_URL}/integrations/${params.id}`,
      {
        method: "PATCH",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      }
    );

    const text = await resp.text();
    const data = text ? JSON.parse(text) : {};
    return NextResponse.json(data, { status: resp.status });
  } catch (e) {
    return NextResponse.json(
      { status: "error", error: "Failed to update integration" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const headers = await getAuthHeaders();
    const url = new URL(`${process.env.API_URL}/integrations/${params.id}`);

    const response = await fetch(url.toString(), {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to delete integration" },
        { status: response.status }
      );
    }

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    return NextResponse.json(data);
  } catch (e) {
    console.error(e);
    return NextResponse.json(
      { status: "error", error: "Failed to delete integration" },
      { status: 500 }
    );
  }
}
