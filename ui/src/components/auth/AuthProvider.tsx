"use client";

import React, { createContext, useContext, useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { getCookie, setCookie } from "@/lib/utils";
import Loader from "@/components/ui/Loader";

// We'll keep this minimal interface for backwards compatibility
interface AuthContextType {
  user: any | null;
  login: (userData: any) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const router = useRouter();
  const pathname = usePathname();
  const {
    user,
    token,
    isLoading,
    isAuthenticated,
    login: storeLogin,
    logout: storeLogout,
    setLoading,
  } = useAuthStore();

  const protectedRoutes = ["/", "/history", "/settings"];

  useEffect(() => {
    const checkUserSession = async () => {
      setLoading(true);
      try {
        // First check if user is admin, since this is an open route
        const adminCheckResponse = await fetch(`/api/auth/admin-check`, {
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (adminCheckResponse.ok) {
          const { is_admin } = await adminCheckResponse.json();
          if (is_admin) {
            router.push("/welcome");
            setLoading(false);
            return;
          }
        }

        // If not admin, proceed with normal authentication flow
        // Try to get token from the store first
        let currentToken = token;

        // If no token in store, try to get it from cookies
        if (!currentToken) {
          currentToken = getCookie("auth_token");

          // If we found a token in cookies but not in store, update the store
          if (currentToken && !token) {
            storeLogin(
              {
                id: "",
                email: "",
                full_name: "",
                role: "",
                is_active: false,
                is_superuser: false,
                is_verified: false,
                created_at: "",
              },
              currentToken
            );
          }
        } else {
          // If we have a token in store but not in cookies, set it in cookies for redundancy
          if (!getCookie("auth_token") && currentToken) {
            setCookie("auth_token", currentToken, 7); // 7 days
          }
        }

        if (!currentToken) {
          // If no token, user is not authenticated
          setLoading(false);

          // If user is trying to access a protected route, redirect to login
          if (protectedRoutes.includes(pathname)) {
            router.push("/login");
          }
          return;
        }

        // If we already have user data, no need to fetch again
        if (user && isAuthenticated) {
          // If user is on the login page but already logged in, redirect to dashboard
          if (pathname === "/login") {
            router.push("/");
          }
          setLoading(false);
          return;
        }

        // Otherwise fetch user data using the token
        const response = await fetch(`/api/auth/me`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${currentToken}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          // Save token to cookie on the client side as well for redundancy
          setCookie("auth_token", currentToken, 7); // 7 days
          storeLogin(userData, currentToken);

          // If user is on the login page but already logged in, redirect to dashboard
          if (pathname === "/login") {
            router.push("/");
          }
        } else {
          // Token is invalid, clear it
          storeLogout();

          // If user is trying to access a protected route, redirect to login
          if (protectedRoutes.includes(pathname)) {
            router.push("/login");
          }
        }
      } catch (error) {
        storeLogout();

        // If there is an error and the user is on a protected route, redirect to login
        if (protectedRoutes.includes(pathname)) {
          router.push("/login");
        }
        console.error("Failed to fetch user session:", error);
      } finally {
        setLoading(false);
      }
    };

    checkUserSession();
  }, [pathname, token, user, isAuthenticated]);

  // Provide backward compatibility wrapper functions
  const login = (userData: any) => {
    storeLogin(userData, token || "");
  };

  const logout = async () => {
    // Also remove from client-side cookies
    if (typeof document !== "undefined") {
      document.cookie =
        "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    }
    storeLogout();
    router.push("/login");
  };

  // For backward compatibility
  const contextValue = {
    user,
    login,
    logout,
    loading: isLoading,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {isLoading ? (
        <div className="flex items-center justify-center h-screen bg-dark">
          <Loader />
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
