"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
} from "react";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import Loader from "@/components/ui/Loader";
import { ACCESS_TOKEN_MAX_AGE_SECONDS } from "@/lib/auth/constants";

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
    isLoading,
    isAuthenticated,
    login: storeLogin,
    logout: storeLogout,
    setLoading,
  } = useAuthStore();

  const protectedRoutes = ["/", "/history", "/settings", "/chat"];
  const initialAuthCheckRef = useRef(false);
  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pathnameRef = useRef(pathname);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isProtectedRoute = (pathname: string) => {
    return protectedRoutes.some((route) => {
      if (route === "/") {
        return pathname === "/";
      }
      return pathname.startsWith(route);
    });
  };

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
  }, []);

  const abortPendingRefresh = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const refreshSession = useCallback(
    async (signal?: AbortSignal): Promise<boolean> => {
      try {
        const refreshResponse = await fetch(`/api/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          signal,
        });

        if (!refreshResponse.ok) {
          return false;
        }

        const refreshData = await refreshResponse.json();
        if (refreshData?.user) {
          storeLogin(refreshData.user, "");
        }
        return true;
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return false;
        }
        return false;
      }
    },
    [storeLogin]
  );

  const scheduleRefresh = useCallback(() => {
    clearRefreshTimer();
    abortPendingRefresh();

    const bufferSeconds = 60;
    const delayMs = Math.max(
      1000,
      (ACCESS_TOKEN_MAX_AGE_SECONDS - bufferSeconds) * 1000
    );

    refreshTimeoutRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const refreshed = await refreshSession(controller.signal);
      abortControllerRef.current = null;

      if (refreshed) {
        scheduleRefresh();
        return;
      }

      storeLogout();
      if (isProtectedRoute(pathnameRef.current)) {
        router.push("/login");
      }
    }, delayMs);
  }, [
    clearRefreshTimer,
    abortPendingRefresh,
    refreshSession,
    storeLogout,
    router,
  ]);

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

        const response = await fetch(`/api/auth/me`, {
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const userData = await response.json();
          storeLogin(userData, "");
          scheduleRefresh();
          return;
        }

        if (response.status === 401) {
          const refreshed = await refreshSession();
          if (refreshed) {
            scheduleRefresh();
            return;
          }
        }

        storeLogout();
        if (isProtectedRoute(pathname)) {
          router.push("/login");
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
    pathnameRef.current = pathname;
  }, [pathname]);

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
    if (!initialAuthCheckRef.current) return;
    if (isAuthenticated) {
      scheduleRefresh();
    } else {
      clearRefreshTimer();
      abortPendingRefresh();
    }
    return () => {
      clearRefreshTimer();
      abortPendingRefresh();
    };
  }, [
    isAuthenticated,
    scheduleRefresh,
    clearRefreshTimer,
    abortPendingRefresh,
  ]);

  const login = (userData: any) => {
    storeLogin(userData, "");
  };

  const logout = async () => {
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        console.error(
          "Logout request failed:",
          response.status,
          response.statusText
        );
      }
    } catch (error) {
      console.error("Logout request error:", error);
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
