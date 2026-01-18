"use client";

import React from "react";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";

import { DailyMetrics } from "@/types/analytics";

interface TokenUsageChartProps {
    data: DailyMetrics[];
}

export default function TokenUsageChart({ data }: TokenUsageChartProps) {
    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorPrompt" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorCompletion" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorCached" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff10" />
                    <XAxis
                        dataKey="date"
                        tickFormatter={(value) => {
                            const [, mm, dd] = String(value).split("-");
                            return `${Number(mm)}/${Number(dd)}`;
                        }}
                        stroke="#9ca3af"
                        tick={{ fill: "#9ca3af", fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="#9ca3af"
                        tick={{ fill: "#9ca3af", fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => (value >= 1000 ? `${value / 1000}k` : value)}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#1c1e24",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: "8px",
                        }}
                        itemStyle={{ color: "#fff" }}
                        labelFormatter={(label) => String(label)}
                    />
                    <Area
                        type="monotone"
                        dataKey="cached_tokens"
                        stackId="1"
                        stroke="#8b5cf6"
                        fill="url(#colorCached)"
                        name="Cached"
                        animationDuration={1500}
                    />
                    <Area
                        type="monotone"
                        dataKey="prompt_tokens"
                        stackId="1"
                        stroke="#3b82f6"
                        fill="url(#colorPrompt)"
                        name="Prompt"
                        animationDuration={1500}
                    />
                    <Area
                        type="monotone"
                        dataKey="completion_tokens"
                        stackId="1"
                        stroke="#10b981"
                        fill="url(#colorCompletion)"
                        name="Completion"
                        animationDuration={1500}
                    />
                    <Legend />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
