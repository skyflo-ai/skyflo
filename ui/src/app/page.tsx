"use client";

import React from "react";
import Navbar from "@/components/navbar/Navbar";
import { Welcome } from "@/components/chat";

export default function HomePage() {
  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow">
        <Welcome />
      </div>
    </div>
  );
}
