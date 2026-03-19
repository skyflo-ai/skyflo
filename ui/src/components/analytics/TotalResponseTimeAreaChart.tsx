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

const CHART_COLOR = "#f472b6";

interface TotalResponseTimeAreaChartProps {
  data: DailyMetrics[];
}

export default function TotalResponseTimeAreaChart({
  data,
}: TotalResponseTimeAreaChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    avg_ttr_ms: d.avg_ttr_ms ?? null,
  }));

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
        >
          <defs>
            <linearGradient id="gradTTR" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLOR} stopOpacity={0.2} />
              <stop offset="100%" stopColor={CHART_COLOR} stopOpacity={0} />
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
            tickFormatter={(v) => `${v}ms`}
          />
          <Tooltip
            cursor={{ stroke: "rgba(255,255,255,0.06)", strokeWidth: 1 }}
            content={
              <ChartTooltip
                valueFormatter={(v) => `${v.toFixed(0)}ms`}
              />
            }
          />
          <Area
            type="monotone"
            dataKey="avg_ttr_ms"
            name="Response Time"
            stroke={CHART_COLOR}
            strokeWidth={1.5}
            fill="url(#gradTTR)"
            activeDot={{ r: 3, fill: CHART_COLOR, strokeWidth: 0 }}
            animationDuration={1200}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
