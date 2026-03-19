"use client";

import React from "react";

interface TooltipPayloadItem {
  name: string;
  value: number;
  color: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
  valueFormatter?: (value: number, name: string) => string;
  labelFormatter?: (label: string) => string;
}

function isTimeBucket(dateStr: string): boolean {
  return (
    dateStr.includes("T") &&
    !dateStr.includes("T00:00:00") &&
    !dateStr.includes("T00:00")
  );
}

export function formatChartDate(dateStr: string): string {
  const raw = String(dateStr);
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }

  if (isTimeBucket(raw)) {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }).format(date);
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatAxisDate(value: string): string {
  const raw = String(value);
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }

  if (isTimeBucket(raw)) {
    return new Intl.DateTimeFormat("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }).format(date);
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "numeric",
    day: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export default function ChartTooltip({
  active,
  payload,
  label,
  valueFormatter,
  labelFormatter,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const displayLabel = labelFormatter
    ? labelFormatter(String(label))
    : formatChartDate(String(label || ""));

  return (
    <div className="rounded-lg bg-zinc-950/90 backdrop-blur-sm border border-white/[0.08] px-3.5 py-2.5 shadow-2xl min-w-[140px]">
      {displayLabel && (
        <p className="text-[11px] font-medium text-zinc-500 mb-2 pb-2 border-b border-white/[0.06]">
          {displayLabel}
        </p>
      )}
      <div className="space-y-1.5">
        {payload
          .filter((entry) => entry.value != null)
          .map((entry, i) => (
            <div key={i} className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-[11px] text-zinc-400">{entry.name}</span>
              </div>
              <span className="text-[11px] font-medium text-white tabular-nums">
                {valueFormatter
                  ? valueFormatter(entry.value, entry.name)
                  : typeof entry.value === "number"
                    ? entry.value.toLocaleString()
                    : entry.value}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
