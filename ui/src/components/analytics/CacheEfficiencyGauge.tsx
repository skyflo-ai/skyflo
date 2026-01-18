"use client";

import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Label } from "recharts";

interface CacheEfficiencyGaugeProps {
    hitRate: number; // 0.0 to 1.0
}

export default function CacheEfficiencyGauge({ hitRate }: CacheEfficiencyGaugeProps) {
    const safeHitRate = Math.max(0, Math.min(1, hitRate || 0));
    const percentage = Math.round(safeHitRate * 100);

    const data = [
        { name: "Hit", value: percentage },
        { name: "Miss", value: 100 - percentage },
    ];

    const cacheEfficiencyColor =
        percentage < 50
            ? "#ff7373"
            : percentage < 60
                ? "#ff9257"
                : percentage < 70
                    ? "#ffa55c"
                    : percentage < 80
                        ? "#fcde60"
                        : percentage < 90
                            ? "#c6ff6b"
                            : "#73ffa6";

    const COLORS = [cacheEfficiencyColor, "#333333"];



    return (
        <div className="h-[300px] w-full flex flex-col items-center justify-center relative">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        innerRadius={80}
                        outerRadius={100}
                        startAngle={90}
                        endAngle={-270}
                        dataKey="value"
                        stroke="none"
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                        <Label
                            value={`${percentage}%`}
                            position="center"
                            fill="#fff"
                            style={{
                                fontSize: "32px",
                                fontWeight: "bold",
                                filter: `drop-shadow(0px 0px 5px ${cacheEfficiencyColor})`,
                            }}
                        />
                    </Pie>
                </PieChart>
            </ResponsiveContainer>
            <div className="absolute bottom-4 text-sm">
                Cache Hit Rate
            </div>
        </div>
    );
}
