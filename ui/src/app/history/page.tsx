"use client";

import React from "react";
import Navbar from "@/components/navbar/Navbar";
import History from "@/components/History";

export default function HistoryPage() {
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
