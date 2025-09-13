"use client";

import React from "react";
import Navbar from "@/components/navbar/Navbar";
import Integrations from "@/components/Integrations";

export default function IntegrationsPage() {
  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow p-6 overflow-y-auto">
        <div className="mx-auto">
          <Integrations />
        </div>
      </div>
    </div>
  );
}
