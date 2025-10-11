"use client";

import { Login } from "@/components/auth/Login";
import { useEffect, useState } from "react";
import { MdLockPerson } from "react-icons/md";

export default function LoginPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#030712]">
        <div className="h-8 w-8 rounded-full border-2 border-blue-400 border-r-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#030712] p-4 relative overflow-hidden">
      <div className="absolute left-1/2 top-1/3 -translate-y-1/3 -translate-x-1/2 w-[80%] aspect-square opacity-[0.04] pointer-events-none select-none">
        <img
          src="/logo_vector_transparent.png"
          alt=""
          className="w-full h-full object-contain"
        />
      </div>

      <div
        className="absolute inset-0 bg-[linear-gradient(to_right,#1a1a1a_1px,transparent_1px),linear-gradient(to_bottom,#1a1a1a_1px,transparent_1px)] opacity-50"
        style={{
          backgroundSize: "48px 48px",
        }}
      />

      <div className="absolute top-0 -left-4 w-[40rem] h-[40rem] bg-[#00B7FF] rounded-full mix-blend-multiply filter blur-[128px] opacity-[0.08]" />
      <div className="absolute bottom-0 right-0 w-[40rem] h-[40rem] bg-[#0056B3] rounded-full mix-blend-multiply filter blur-[128px] opacity-[0.08]" />

      <div className="w-full max-w-md space-y-8 relative z-10">
        <div className="text-center space-y-4">
          <div className="text-5xl font-bold text-white">
            <h1 className="text-4xl font-bold tracking-tight my-2 text-center">
              <span className="text-gray-200">skyflo</span>
              <span className="text-[#06B6D4]">.ai</span>
            </h1>
          </div>
          <p className="text-slate-400 text-lg">Sign in to your account</p>
        </div>

        <div className="bg-gradient-to-br from-[#0A1020]/60 to-[#0A1525]/60 rounded-xl border border-[#243147]/30 shadow-[0px_0px_8px_1px_rgba(0,_0,_0,_0.35)] overflow-hidden backdrop-blur-sm">
          <div className="bg-gradient-to-r from-[#1A2C48]/80 to-[#0F182A]/80 p-5 border-b border-[#243147]/30 backdrop-blur-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-[#00B7FF]/10 p-2.5 rounded-full">
                <MdLockPerson className="w-5 h-5 text-[#00B7FF]" />
              </div>
              <h2 className="text-xl font-semibold text-white">Sign In</h2>
            </div>
          </div>
          <div className="p-6">
            <Login />
          </div>
        </div>
      </div>
    </div>
  );
}
