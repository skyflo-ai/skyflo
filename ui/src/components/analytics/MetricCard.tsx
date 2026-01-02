"use client";

import React from "react";
import { motion } from "framer-motion";

interface MetricCardProps {
    title: string;
    value: string;
    trend?: number | null;
    icon: React.ReactNode;
    color?: string;
}

export default function MetricCard({ title, value, trend, icon, color }: MetricCardProps) {
    return (
        <motion.div
            variants={{
                hidden: { y: 20, opacity: 0 },
                visible: { y: 0, opacity: 1 },
            }}
            className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 inline-block transition-colors group"
        >
            <div className="flex justify-between items-start mb-4">
                <span className="text-text-secondary text-sm font-medium">{title}</span>
                <span className={`text-2xl opacity-80 group-hover:scale-110 transition-transform duration-300`}>
                    {icon}
                </span>
            </div>
            <div className="flex items-end gap-3">
                <span className={`text-3xl font-bold tracking-tight ${color || "text-white"}`}>
                    {value}
                </span>
                {trend !== null && trend !== undefined && (
                    <span
                        className={`text-sm mb-1 font-medium ${trend >= 0 ? "text-green-500" : "text-red-500"
                            }`}
                    >
                        {trend >= 0 ? "↑" : "↓"} {Math.abs(trend)}%
                    </span>
                )}
            </div>
        </motion.div>
    );
}
