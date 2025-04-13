"use client";

import React from "react";
import Navbar from "@/components/navbar/Navbar";
import Welcome from "@/components/chat/components/Welcome";

import { MdElectricBolt, MdSearch, MdDelete, MdRefresh } from "react-icons/md";

const INITIAL_SUGGESTIONS = [
  {
    text: "Get all pods in the ... namespace",
    icon: MdSearch,
    category: "Query",
  },
  {
    text: "Create a new deployment with nginx:latest in the ... namespace",
    icon: MdElectricBolt,
    category: "Create Deployment",
  },
  {
    text: "Restart the api deployment in the ... namespace",
    icon: MdRefresh,
    category: "Restart Deployment",
  },
  {
    text: "Delete the frontend deployment in the ... namespace",
    icon: MdDelete,
    category: "Delete Resource",
  },
];

export default function HomePage() {
  return (
    <div className="flex h-screen w-full bg-background">
      <Navbar />
      <div className="flex-grow">
        <Welcome initialSuggestions={INITIAL_SUGGESTIONS} />
      </div>
    </div>
  );
}
