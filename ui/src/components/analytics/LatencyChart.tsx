"use client";

import React from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";

interface DailyMetrics {
    date: string;
    avg_ttft_ms: number | null;
    avg_ttr_ms: number | null;
}

interface LatencyChartProps {
    data: DailyMetrics[];
}

export default function LatencyChart({ data }: LatencyChartProps) {
    // Filter out days with no data to avoid gaps or messy charts
    const chartData = data.map((d) => ({
        ...d,
        avg_ttft_ms: d.avg_ttft_ms || 0,
        avg_ttr_ms: d.avg_ttr_ms || 0,
    }));

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
                        label={{ value: "ms", angle: -90, position: "insideLeft", fill: "#9ca3af" }}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#1c1e24",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: "8px",
                        }}
                        itemStyle={{ color: "#fff" }}
                        labelFormatter={(label) => new Date(label).toLocaleDateString()}
                    />
                    <Legend wrapperStyle={{ paddingTop: "10px" }} />
                    <Line
                        type="monotone"
                        dataKey="avg_ttft_ms"
                        name="TTFT (Time to First Token)"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                        animationDuration={1500}
                    />
                    <Line
                        type="monotone"
                        dataKey="avg_ttr_ms"
                        name="TTR (Total Response Time)"
                        stroke="#ec4899"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                        animationDuration={1500}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
