import { NextRequest, NextResponse } from "next/server";
import { getAuthHeaders } from "@/lib/api";

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(
      `${process.env.API_URL}/conversations/${params.id}`,
      {
        method: "GET",
        headers,
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to fetch conversation details" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to fetch conversation details" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const headers = await getAuthHeaders();
    const body = await request.json();

    const response = await fetch(
      `${process.env.API_URL}/conversations/${params.id}`,
      {
        method: "PATCH",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to update conversation" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to update conversation" },
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

    const response = await fetch(
      `${process.env.API_URL}/conversations/${params.id}`,
      {
        method: "DELETE",
        headers,
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to delete conversation" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", error: "Failed to delete conversation" },
      { status: 500 }
    );
  }
}
