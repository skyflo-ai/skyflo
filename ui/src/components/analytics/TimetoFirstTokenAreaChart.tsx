"use client";

import React from "react";
import {
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
    AreaChart,
} from "recharts";

import { DailyMetrics } from "@/types/analytics";

interface TimetoFirstTokenAreaChartProps {
    data: DailyMetrics[];
}

export default function TimetoFirstTokenAreaChart({ data }: TimetoFirstTokenAreaChartProps) {
    const chartData = data.map((d) => ({
        ...d,
        avg_ttft_ms: d.avg_ttft_ms || 0,
        avg_ttr_ms: d.avg_ttr_ms || 0,
    }));

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorTTFT" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
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
                        label={{ value: "ms", angle: -90, position: "insideLeft", fill: "#9ca3af" }}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#1c1e24",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: "8px",
                        }}
                        itemStyle={{ color: "#fff" }}
                        labelFormatter={(label) => String(label)}
                        formatter={(value: number) => [`${value.toFixed(4)}ms`, "TTFT (Time to First Token)"]}
                    />
                    <Legend wrapperStyle={{ paddingTop: "10px" }} />
                    <Area
                        type="monotone"
                        dataKey="avg_ttft_ms"
                        stroke="#f59e0b"
                        fill="url(#colorTTFT)"
                        name="TTFT (Time to First Token)"
                        animationDuration={1500}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
