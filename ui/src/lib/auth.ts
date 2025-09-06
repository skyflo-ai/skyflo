"use server";

import { cookies } from "next/headers";
import { AuthToken, User } from "../types/auth";

type AuthResult =
  | { success: true; user: User; token: string; error?: undefined }
  | { success: false; error: string };

export async function handleLogin(formData: FormData): Promise<AuthResult> {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  try {
    const urlSearchParams = new URLSearchParams();
    urlSearchParams.append("username", email);
    urlSearchParams.append("password", password);

    const response = await fetch(`${process.env.API_URL}/auth/jwt/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: urlSearchParams.toString(),
    });

    if (response.ok) {
      const tokenData: AuthToken = await response.json();

      cookies().set("auth_token", tokenData.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        maxAge: 60 * 60 * 24 * 7, // 1 week
        path: "/",
      });

      const userResponse = await fetch(`${process.env.API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${tokenData.access_token}`,
        },
      });

      if (userResponse.ok) {
        const userData: User = await userResponse.json();
        return {
          success: true,
          user: userData,
          token: tokenData.access_token,
        };
      } else {
        return { success: false, error: "Failed to fetch user data" };
      }
    } else {
      return { success: false, error: "Authentication failed" };
    }
  } catch (error) {
    return { success: false, error: "Error during login" };
  }
}

export async function handleRegistration(
  formData: FormData
): Promise<AuthResult> {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const name = formData.get("name") as string;
  try {
    const response = await fetch(
      `${process.env.API_URL}/auth/register/register/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: name,
          email,
          password,
        }),
        credentials: "include",
      }
    );

    if (response.ok) {
      const userData = await response.json();

      return { success: true, user: userData, token: "" };
    } else {
      return { success: false, error: "Registration failed" };
    }
  } catch (error) {
    return { success: false, error: "Error during registration" };
  }
}

export async function handleLogout() {
  try {
    const nextCookies = cookies().getAll();
    const cookieHeader = nextCookies
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const response = await fetch(`${process.env.API_URL}/auth/jwt/logout/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Cookie: cookieHeader,
      },
    });

    if (response.ok) {
      cookies().delete("auth_token");

      nextCookies.forEach((cookie) => {
        cookies().delete(cookie.name);
      });

      return { success: true };
    } else if (response.status === 401) {
      return { success: false, error: "Unauthorized" };
    }
  } catch (error) {
    return { success: false, error: "Error during logout" };
  }
}

export async function updateUserProfile(data: {
  full_name?: string;
}): Promise<{ success: boolean; user?: User; error?: string }> {
  try {
    const nextCookies = cookies().getAll();
    const cookieHeader = nextCookies
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const authToken = nextCookies.find(
      (cookie) => cookie.name === "auth_token"
    );

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(`${process.env.API_URL}/auth/me`, {
      method: "PATCH",
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
        error: errorData.detail || "Failed to update profile",
      };
    }

    const updatedUser = await response.json();
    return { success: true, user: updatedUser };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function changePassword(data: {
  current_password: string;
  new_password: string;
}): Promise<{ success: boolean; error?: string }> {
  try {
    const nextCookies = cookies().getAll();
    const authToken = nextCookies.find(
      (cookie) => cookie.name === "auth_token"
    );

    if (!authToken) {
      return { success: false, error: "Authentication token not found" };
    }

    const response = await fetch(
      `${process.env.API_URL}/auth/users/me/password`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken.value}`,
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "Failed to change password",
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
