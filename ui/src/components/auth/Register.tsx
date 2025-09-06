"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AuthInput } from "./AuthInput";
import { MdLock, MdEmail, MdPerson } from "react-icons/md";
import { useAuthStore } from "@/store/useAuthStore";
import { handleRegistration } from "@/lib/auth";

export const Register = () => {
  const { login } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!isMounted) return;

    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const result = await handleRegistration(formData);

    if (result && result.success) {
      router.push("/login");
    } else {
      setError(result?.error || "Registration failed");
    }

    setLoading(false);
  };

  if (!isMounted) {
    return null;
  }

  return (
    <form onSubmit={handleSubmit}>
      <AuthInput
        id="name"
        type="text"
        name="name"
        placeholder="Your Name"
        icon={MdPerson}
      />
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
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mt-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}
      <Button
        className="w-full mt-4 bg-gradient-to-r from-[#00B7FF] to-[#0056B3] text-white border-0 leading-tight py-6 rounded-lg font-semibold shadow-lg hover:shadow-xl hover:brightness-110 transition-all duration-300"
        type="submit"
        disabled={loading}
      >
        {loading ? (
          <div className="flex items-center justify-center gap-2">
            <div className="h-4 w-4 rounded-full border-2 border-white border-r-transparent animate-spin" />
            <span>Creating admin account...</span>
          </div>
        ) : (
          "Create Admin Account"
        )}
      </Button>
    </form>
  );
};
