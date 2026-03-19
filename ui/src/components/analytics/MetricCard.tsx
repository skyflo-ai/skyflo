"use client";

import React from "react";
import { motion } from "framer-motion";
import { AnimatedCounter } from "./AnimatedCounter";

interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  valueColor?: string;
}

export default function MetricCard({ title, value, icon, valueColor }: MetricCardProps) {
  return (
    <motion.div
      variants={{
        hidden: { y: 12, opacity: 0 },
        visible: { y: 0, opacity: 1 },
      }}
      className="relative overflow-hidden rounded-xl bg-white/[0.03] border border-white/[0.06] p-5 hover:border-white/[0.12] transition-colors duration-200 group"
    >
      <div className="flex items-start justify-between mb-4">
        <span className="text-xs font-medium text-zinc-500 leading-tight pr-2">
          {title}
        </span>
        <div
          className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm shrink-0 group-hover:scale-105 transition-transform duration-200"
        >
          {icon}
        </div>
      </div>

      <AnimatedCounter
        value={value}
        className={`text-2xl font-semibold tracking-tight ${valueColor ?? "text-white"}`}
      />
    </motion.div>
  );
}
