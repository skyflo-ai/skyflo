"use client";

import React from "react";
import {
    AreaChart,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Area,
} from "recharts";

import { DailyMetrics } from "@/types/analytics";

interface TotalResponseTimeLineChartProps {
    data: DailyMetrics[];
}

export default function TotalResponseTimeLineChart({ data }: TotalResponseTimeLineChartProps) {
    const chartData = data.map((d) => ({
        ...d,
        avg_ttr_ms: d.avg_ttr_ms || 0,
    }));
    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorTTR" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ec4899" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff10" />
                    <XAxis
                        dataKey="date"
                        tickFormatter={(value) => String(value)}
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
                        tickFormatter={(value) => `${value}ms`}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#1c1e24",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: "8px",
                        }}
                        itemStyle={{ color: "#fff" }}
                        labelFormatter={(label) => String(label)}
                        formatter={(value: number) => [`${value.toFixed(4)}ms`, "Total Response Time"]}
                    />
                    <Area
                        type="monotone"
                        dataKey="avg_ttr_ms"
                        stroke="#ec4899"
                        fill="url(#colorTTR)"
                        name="TTR (Total Response Time)"
                        animationDuration={1500}
                    />
                    <Legend />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
