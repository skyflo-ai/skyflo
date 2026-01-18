"use client";

import React from "react";
import { motion } from "framer-motion";
import { AnimatedCounter } from "./AnimatedCounter";

interface MetricCardProps {
    title: string;
    value: string;
    icon: React.ReactNode;
    color?: string;
}

export default function MetricCard({ title, value, icon, color }: MetricCardProps) {
    return (
        <motion.div
            variants={{
                hidden: { y: 20, opacity: 0 },
                visible: { y: 0, opacity: 1 },
            }}
            className="bg-navbar rounded-lg border border-slate-700/60 p-8 inline-block transition-colors group"
        >
            <div className="flex justify-between items-start mb-4">
                <span className=" text-sm font-medium">{title}</span>
                <span className={`text-2xl opacity-80 group-hover:scale-110 transition-transform duration-300`}>
                    {icon}
                </span>
            </div>
            <div className="flex items-end gap-3">
                <AnimatedCounter
                    value={value}
                    className={`text-3xl font-bold tracking-tight ${color || "text-white"}`}
                />
            </div>
        </motion.div>
    );
}
