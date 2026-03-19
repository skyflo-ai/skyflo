"use client";

import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

const THRESHOLD_COLORS: [number, string][] = [
  [50, "#f87171"],
  [60, "#fb923c"],
  [70, "#fbbf24"],
  [80, "#facc15"],
  [90, "#a3e635"],
  [Infinity, "#34d399"],
];

function getColor(percentage: number): string {
  for (const [threshold, color] of THRESHOLD_COLORS) {
    if (percentage < threshold) return color;
  }
  return THRESHOLD_COLORS[THRESHOLD_COLORS.length - 1][1];
}

interface CacheEfficiencyGaugeProps {
  hitRate: number;
}

export default function CacheEfficiencyGauge({
  hitRate,
}: CacheEfficiencyGaugeProps) {
  const percentage = Math.round(
    Math.max(0, Math.min(1, hitRate || 0)) * 100,
  );
  const fillColor = getColor(percentage);

  const data = [
    { name: "Hit", value: percentage },
    { name: "Miss", value: 100 - percentage },
  ];

  return (
    <div className="h-full w-full flex flex-col items-center justify-center min-h-[240px]">
      <div className="relative w-full flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="75%"
              startAngle={90}
              endAngle={-270}
              dataKey="value"
              stroke="none"
              animationDuration={1200}
            >
              <Cell fill={fillColor} />
              <Cell fill="rgba(255,255,255,0.04)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span
            className="text-3xl font-bold tabular-nums"
            style={{ color: fillColor }}
          >
            {percentage}%
          </span>
          <span className="text-[11px] text-zinc-500 mt-1">Hit Rate</span>
        </div>
      </div>
    </div>
  );
}
