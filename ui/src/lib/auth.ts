"use server";

import { cookies } from "next/headers";
import { AuthToken, User } from "./types/auth";

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

      // Store token in cookies for server-side access
      cookies().set("auth_token", tokenData.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        maxAge: 60 * 60 * 24 * 7, // 1 week
        path: "/",
      });

      // Get user data
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
    console.error("Error during login:", error);
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
      const setCookieHeader = response.headers.get("set-cookie");

      if (setCookieHeader) {
        const cookieArray = setCookieHeader.split(/,(?=[^;]+=[^;]+)/);

        cookieArray.forEach((cookieStr) => {
          const [name, value] = cookieStr.split(";")[0].trim().split("=");
          cookies().set(name, value, {
            path: "/",
            httpOnly: cookieStr.includes("HttpOnly"),
            secure: cookieStr.includes("Secure"),
            sameSite: getSameSite(cookieStr),
            maxAge: getMaxAge(cookieStr),
            expires: getExpires(cookieStr),
          });
        });
      }

      return { success: true, user: userData, token: "" };
    } else {
      return { success: false, error: "Registration failed" };
    }
  } catch (error) {
    console.error("Error during registration:", error);
    return { success: false, error: "Error during registration" };
  }
}

function getSameSite(cookieStr: string): "strict" | "lax" | "none" | undefined {
  if (cookieStr.includes("SameSite=None")) return "none";
  if (cookieStr.includes("SameSite=Strict")) return "strict";
  if (cookieStr.includes("SameSite=Lax")) return "lax";
  return undefined;
}

function getMaxAge(cookieStr: string): number | undefined {
  const maxAgeMatch = cookieStr.match(/Max-Age=(\d+)/);
  return maxAgeMatch ? parseInt(maxAgeMatch[1], 10) : undefined;
}

function getExpires(cookieStr: string): Date | undefined {
  const expiresMatch = cookieStr.match(/expires=([^;]+)/i);
  return expiresMatch ? new Date(expiresMatch[1]) : undefined;
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
      // Remove auth cookie
      cookies().delete("auth_token");

      // Clear any other cookies if needed
      nextCookies.forEach((cookie) => {
        cookies().delete(cookie.name);
      });

      return { success: true };
    } else if (response.status === 401) {
      return { success: false, error: "Unauthorized" };
    }
  } catch (error) {
    console.error("Error during logout:", error);
    return { success: false, error: "Error during logout" };
  }
}

// Server-side API function to update user profile
export async function updateUserProfile(data: {
  full_name?: string;
}): Promise<{ success: boolean; user?: User; error?: string }> {
  try {
    // Get the auth token from server-side cookies
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
    console.error("Error updating profile:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

// Server-side API function to change password
export async function changePassword(data: {
  current_password: string;
  new_password: string;
}): Promise<{ success: boolean; error?: string }> {
  try {
    // Get the auth token from server-side cookies
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
    console.error("Error changing password:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}
