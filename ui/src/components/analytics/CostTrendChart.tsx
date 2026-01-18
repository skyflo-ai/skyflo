"use client";

import React from "react";
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    AreaChart,
    Area,
} from "recharts";

import { DailyMetrics } from "@/types/analytics";

interface CostTrendChartProps {
    data: DailyMetrics[];
}

export default function CostTrendChart({ data }: CostTrendChartProps) {
    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff10" />
                    <XAxis
                        dataKey="date"
                        tickFormatter={(value) => {
                            const date = new Date(value);
                            return `${date.getMonth() + 1}/${date.getDate()}`;
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
                        tickFormatter={(value) => `$${value}`}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#1c1e24",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: "8px",
                        }}
                        itemStyle={{ color: "#fff" }}
                        labelFormatter={(label) => new Date(label).toLocaleDateString()}
                        formatter={(value: number) => [`$${value.toFixed(4)}`, "Cost"]}
                    />
                    <Area
                        type="monotone"
                        dataKey="cost"
                        name="Cost"
                        stroke="#10b981"
                        fill="url(#colorCost)"
                        animationDuration={1500}
                    />


                    <Legend />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
