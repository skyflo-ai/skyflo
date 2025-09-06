import { NextRequest, NextResponse } from "next/server";
import { updateUserProfile, changePassword } from "@/lib/auth";

export async function PATCH(request: NextRequest) {
  try {
    const data = await request.json();

    const result = await updateUserProfile(data);

    if (result.success) {
      return NextResponse.json(result.user, { status: 200 });
    } else {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to update profile" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    if (data.new_password && data.new_password.length < 8) {
      return NextResponse.json(
        { error: "Password must be at least 8 characters long" },
        { status: 400 }
      );
    }

    if (data.new_password !== data.confirm_password) {
      return NextResponse.json(
        { error: "Passwords do not match" },
        { status: 400 }
      );
    }

    const result = await changePassword({
      current_password: data.current_password,
      new_password: data.new_password,
    });

    if (result.success) {
      return NextResponse.json(
        { message: "Password updated" },
        { status: 200 }
      );
    } else {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to change password" },
      { status: 500 }
    );
  }
}
