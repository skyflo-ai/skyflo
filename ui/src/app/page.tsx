"use client";

import React from "react";
import Navbar from "@/components/navbar/Navbar";
import Welcome from "@/components/chat/components/Welcome";

import {
  MdBarChart,
  MdElectricBolt,
  MdSearch,
  MdRefresh,
} from "react-icons/md";

const INITIAL_SUGGESTIONS = [
  {
    text: "Get the cluster info.",
    icon: MdSearch,
    category: "Query",
  },
  {
    text: "Get the list of pods running in the prod namespace.",
    icon: MdElectricBolt,
    category: "Restart Deployment",
  },
  {
    text: "Fix the api-prod deployment in the prod namespace",
    icon: MdBarChart,
    category: "Analyze",
  },
  {
    text: "Let's create a new deployment that uses nginx:latest and runs in the prod namespace",
    icon: MdRefresh,
    category: "Create Deployment",
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
