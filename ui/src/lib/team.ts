"use server";

import { cookies } from "next/headers";
import { TeamMember } from "../types/auth";

export async function getTeamMembers(): Promise<{
  success: boolean;
  members?: TeamMember[];
  error?: string;
}> {
  try {
    const authToken = cookies().get("auth_token");

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(`${process.env.API_URL}/team/members`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken.value}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error:
          typeof errorData.detail === "object"
            ? errorData.detail.msg || JSON.stringify(errorData.detail)
            : errorData.detail || "Failed to fetch team members",
      };
    }

    const members = await response.json();
    return { success: true, members };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function inviteTeamMember(data: {
  email: string;
  role: string;
  password: string;
}): Promise<{ success: boolean; member?: TeamMember; error?: string }> {
  try {
    const authToken = cookies().get("auth_token");

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(`${process.env.API_URL}/team/members`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken.value}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "Failed to invite team member",
      };
    }

    const member = await response.json();
    return { success: true, member };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function removeTeamMember(
  memberId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const authToken = cookies().get("auth_token");

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(
      `${process.env.API_URL}/team/members/${memberId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${authToken.value}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "Failed to remove team member",
      };
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function updateTeamMemberRole(data: {
  memberId: string;
  role: string;
}): Promise<{ success: boolean; member?: TeamMember; error?: string }> {
  try {
    const authToken = cookies().get("auth_token");

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(
      `${process.env.API_URL}/team/members/${data.memberId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken.value}`,
        },
        body: JSON.stringify({ role: data.role }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "Failed to update team member role",
      };
    }

    const member = await response.json();
    return { success: true, member };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function getPendingInvitations(): Promise<{
  success: boolean;
  invitations?: TeamMember[];
  error?: string;
}> {
  try {
    const authToken = cookies().get("auth_token");

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(`${process.env.API_URL}/team/invitations`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken.value}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "Failed to fetch pending invitations",
      };
    }

    const invitations = await response.json();
    return { success: true, invitations };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function cancelInvitation(
  invitationId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const authToken = cookies().get("auth_token");

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(
      `${process.env.API_URL}/team/invitations/${invitationId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${authToken.value}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "Failed to cancel invitation",
      };
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}
