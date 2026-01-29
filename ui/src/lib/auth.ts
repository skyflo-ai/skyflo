"use server";

import { cookies } from "next/headers";
import { AuthToken, User } from "../types/auth";
import {
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
} from "./auth/constants";

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
        maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
        sameSite: "lax",
        path: "/",
      });

      const refreshResponse = await fetch(
        `${process.env.API_URL}/auth/refresh/issue`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${tokenData.access_token}`,
          },
        }
      );

      if (!refreshResponse.ok) {
        cookies().delete("auth_token");
        cookies().delete("refresh_token");
        return { success: false, error: "Failed to issue refresh token" };
      }

      const refreshData: { refresh_token?: string } =
        await refreshResponse.json();

      if (!refreshData.refresh_token) {
        cookies().delete("auth_token");
        cookies().delete("refresh_token");
        return { success: false, error: "Invalid refresh token response" };
      }

      cookies().set("refresh_token", refreshData.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
        sameSite: "lax",
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
        cookies().delete("auth_token");
        cookies().delete("refresh_token");
        return { success: false, error: "Failed to fetch user data" };
      }
    } else {
      return { success: false, error: "Authentication failed" };
    }
  } catch (error) {
    cookies().delete("auth_token");
    cookies().delete("refresh_token");
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

export async function updateUserProfile(data: {
  full_name?: string;
}): Promise<{ success: boolean; user?: User; error?: string }> {
  try {
    const nextCookies = cookies().getAll();

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
