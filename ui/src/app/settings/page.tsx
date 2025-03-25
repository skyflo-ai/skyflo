"use client";

import React, { useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import Navbar from "@/components/navbar/Navbar";
import { useAuthStore } from "@/store/useAuthStore";
import ProfileSettings from "@/components/settings/Settings";

export default function SettingsPage() {
  const { user } = useAuth();
  const { user: storeUser } = useAuthStore();

  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow p-6 overflow-y-auto">
        <div className=" mx-auto">
          <ProfileSettings user={storeUser || user} />
        </div>
      </div>
    </div>
  );
}
