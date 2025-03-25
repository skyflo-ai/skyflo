"use client";

import React from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import Navbar from "@/components/navbar/Navbar";
import { useAuthStore } from "@/store/useAuthStore";
import History from "@/components/History";

export default function HistoryPage() {
  const { user } = useAuth();
  const { user: storeUser } = useAuthStore();

  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow p-6 overflow-y-auto">
        <div className="mx-auto">
          <History />
        </div>
      </div>
    </div>
  );
}
