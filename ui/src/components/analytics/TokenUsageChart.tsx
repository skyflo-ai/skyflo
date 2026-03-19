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
} from "recharts";
import ChartTooltip, { formatAxisDate } from "./ChartTooltip";
import { DailyMetrics } from "@/types/analytics";

const COLORS = {
  cached: "#a78bfa",
  input: "#38bdf8",
  output: "#34d399",
};

interface TokenUsageChartProps {
  data: DailyMetrics[];
}

export default function TokenUsageChart({ data }: TokenUsageChartProps) {
  const gradientSuffix = React.useId().replace(/:/g, "");
  const cachedGradientId = `gradCached-${gradientSuffix}`;
  const inputGradientId = `gradInput-${gradientSuffix}`;
  const outputGradientId = `gradOutput-${gradientSuffix}`;

  return (
    <div>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
          >
            <defs>
              <linearGradient id={cachedGradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={COLORS.cached}
                  stopOpacity={0.25}
                />
                <stop
                  offset="100%"
                  stopColor={COLORS.cached}
                  stopOpacity={0}
                />
              </linearGradient>
              <linearGradient id={inputGradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={COLORS.input}
                  stopOpacity={0.25}
                />
                <stop
                  offset="100%"
                  stopColor={COLORS.input}
                  stopOpacity={0}
                />
              </linearGradient>
              <linearGradient id={outputGradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={COLORS.output}
                  stopOpacity={0.25}
                />
                <stop
                  offset="100%"
                  stopColor={COLORS.output}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="rgba(255,255,255,0.04)"
            />
            <XAxis
              dataKey="date"
              tickFormatter={formatAxisDate}
              stroke="transparent"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="transparent"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : `${v}`)}
            />
            <Tooltip
              cursor={{ stroke: "rgba(255,255,255,0.06)", strokeWidth: 1 }}
              content={
                <ChartTooltip
                  valueFormatter={(v) => v.toLocaleString()}
                />
              }
            />
            <Area
              type="monotone"
              dataKey="cached_tokens"
              stackId="tokens"
              stroke={COLORS.cached}
              strokeWidth={1.5}
              fill={`url(#${cachedGradientId})`}
              name="Cached"
              activeDot={false}
              animationDuration={1200}
            />
            <Area
              type="monotone"
              dataKey="prompt_tokens"
              stackId="tokens"
              stroke={COLORS.input}
              strokeWidth={1.5}
              fill={`url(#${inputGradientId})`}
              name="Input"
              activeDot={false}
              animationDuration={1200}
            />
            <Area
              type="monotone"
              dataKey="completion_tokens"
              stackId="tokens"
              stroke={COLORS.output}
              strokeWidth={1.5}
              fill={`url(#${outputGradientId})`}
              name="Output"
              activeDot={false}
              animationDuration={1200}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center gap-5 mt-3 px-1">
        {[
          { label: "Cached", color: COLORS.cached },
          { label: "Input", color: COLORS.input },
          { label: "Output", color: COLORS.output },
        ].map(({ label, color }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[11px] text-zinc-500">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
