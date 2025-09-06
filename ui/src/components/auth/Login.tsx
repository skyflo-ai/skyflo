"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AuthInput } from "./AuthInput";
import { MdLock, MdEmail } from "react-icons/md";
import { useAuthStore } from "@/store/useAuthStore";
import { handleLogin } from "@/lib/auth";
import { setCookie } from "@/lib/utils";
import { showError } from "../ui/toast";

export const Login = () => {
  const { login } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!isMounted) return;

    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const result = await handleLogin(formData);

    if (result && result.success) {
      setCookie("auth_token", result.token, 7);
      login(result.user, result.token);
      router.push("/");
    } else {
      showError(result?.error || "Authentication failed");
    }

    setLoading(false);
  };

  if (!isMounted) {
    return null;
  }

  return (
    <form onSubmit={handleSubmit}>
      <AuthInput
        id="email"
        type="email"
        name="email"
        placeholder="m@example.com"
        icon={MdEmail}
      />
      <AuthInput
        id="password"
        type="password"
        name="password"
        placeholder="••••••••"
        icon={MdLock}
      />
      <Button
        className="w-full mt-4 bg-gradient-to-r from-[#00B7FF] to-[#0056B3] text-white border-0 leading-tight py-6 rounded-lg font-semibold shadow-lg hover:shadow-xl hover:brightness-110 transition-all duration-300"
        type="submit"
        disabled={loading}
      >
        {loading ? (
          <div className="flex items-center justify-center gap-2">
            <div className="h-4 w-4 rounded-full border-2 border-white border-r-transparent animate-spin" />
            <span>Signing in...</span>
          </div>
        ) : (
          "Sign In"
        )}
      </Button>
    </form>
  );
};
