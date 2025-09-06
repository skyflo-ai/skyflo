import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import {
  getTeamMembers,
  inviteTeamMember,
  removeTeamMember,
  updateTeamMemberRole,
  getPendingInvitations,
  cancelInvitation,
} from "@/lib/team";

async function isUserAdmin() {
  try {
    const authToken = cookies().get("auth_token");
    if (!authToken) {
      return false;
    }

    const response = await fetch(`${process.env.API_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${authToken.value}`,
      },
    });

    if (!response.ok) {
      return false;
    }

    const user = await response.json();
    return user.role === "admin";
  } catch (error) {
    return false;
  }
}

export async function GET(req: NextRequest) {
  try {
    const admin = await isUserAdmin();
    if (!admin) {
      return NextResponse.json(
        { error: "Only administrators can access team management" },
        { status: 403 }
      );
    }

    const url = new URL(req.url);
    const path = url.pathname.split("/");
    const endpoint = path[path.length - 1];

    if (endpoint === "invitations") {
      const result = await getPendingInvitations();
      if (result.success) {
        return NextResponse.json(result.invitations);
      } else {
        return NextResponse.json({ error: result.error }, { status: 400 });
      }
    } else {
      const result = await getTeamMembers();
      if (result.success) {
        return NextResponse.json(result.members);
      } else {
        let statusCode = 400;
        if (
          result.error &&
          result.error.includes("Authentication token not found")
        ) {
          statusCode = 401;
        }
        return NextResponse.json(
          { error: result.error },
          { status: statusCode }
        );
      }
    }
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const admin = await isUserAdmin();
    if (!admin) {
      return NextResponse.json(
        { error: "Only administrators can invite team members" },
        { status: 403 }
      );
    }

    const body = await req.json();
    const { email, role, password } = body;

    if (!email) {
      return NextResponse.json({ error: "Email is required" }, { status: 400 });
    }

    if (!password) {
      return NextResponse.json(
        { error: "Password is required" },
        { status: 400 }
      );
    }

    const result = await inviteTeamMember({
      email,
      role: role || "Member",
      password,
    });

    if (result.success) {
      return NextResponse.json(result.member);
    } else {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const admin = await isUserAdmin();
    if (!admin) {
      return NextResponse.json(
        { error: "Only administrators can update team member roles" },
        { status: 403 }
      );
    }

    const body = await req.json();
    const { memberId, role } = body;

    if (!memberId || !role) {
      return NextResponse.json(
        { error: "Member ID and role are required" },
        { status: 400 }
      );
    }

    const result = await updateTeamMemberRole({ memberId, role });
    if (result.success) {
      return NextResponse.json(result.member);
    } else {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const admin = await isUserAdmin();
    if (!admin) {
      return NextResponse.json(
        { error: "Only administrators can remove team members" },
        { status: 403 }
      );
    }

    const url = new URL(req.url);
    const searchParams = url.searchParams;

    const memberId = searchParams.get("memberId");
    const invitationId = searchParams.get("invitationId");

    if (memberId) {
      const result = await removeTeamMember(memberId);
      if (result.success) {
        return NextResponse.json({ success: true });
      } else {
        return NextResponse.json({ error: result.error }, { status: 400 });
      }
    } else if (invitationId) {
      const result = await cancelInvitation(invitationId);
      if (result.success) {
        return NextResponse.json({ success: true });
      } else {
        return NextResponse.json({ error: result.error }, { status: 400 });
      }
    } else {
      return NextResponse.json(
        { error: "Member ID or invitation ID is required" },
        { status: 400 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
}
