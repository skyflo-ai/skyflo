"use client";

import React, { createContext, useContext, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { getCookie, setCookie } from "@/lib/utils";
import Loader from "@/components/ui/Loader";

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

  const protectedRoutes = ["/", "/history", "/settings", "/chat"];
  const initialAuthCheckRef = useRef(false);

  const isProtectedRoute = (pathname: string) => {
    return protectedRoutes.some((route) => {
      if (route === "/") {
        return pathname === "/";
      }
      return pathname.startsWith(route);
    });
  };

  useEffect(() => {
    if (initialAuthCheckRef.current) return;

    const checkUserSession = async () => {
      initialAuthCheckRef.current = true;
      setLoading(true);

      try {
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

        let currentToken = token || getCookie("auth_token");

        if (!currentToken) {
          setLoading(false);
          if (isProtectedRoute(pathname)) {
            router.push("/login");
          }
          return;
        }

        const response = await fetch(`/api/auth/me`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${currentToken}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          setCookie("auth_token", currentToken, 7);
          storeLogin(userData, currentToken);
        } else {
          storeLogout();
          if (isProtectedRoute(pathname)) {
            router.push("/login");
          }
        }
      } catch (error) {
        storeLogout();
        if (isProtectedRoute(pathname)) {
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    };

    checkUserSession();
  }, []);

  useEffect(() => {
    if (isLoading || !initialAuthCheckRef.current) return;

    if (isAuthenticated) {
      if (pathname === "/login") {
        router.push("/");
      }
    } else {
      if (isProtectedRoute(pathname)) {
        router.push("/login");
      }
    }
  }, [pathname, isAuthenticated, isLoading]);

  useEffect(() => {
    const cookieToken = getCookie("auth_token");

    if (token && !cookieToken) {
      setCookie("auth_token", token, 7);
    }
  }, [token]);

  const login = (userData: any) => {
    storeLogin(userData, token || "");
  };

  const logout = async () => {
    if (typeof document !== "undefined") {
      document.cookie =
        "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    }
    storeLogout();
    router.push("/login");
  };

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
