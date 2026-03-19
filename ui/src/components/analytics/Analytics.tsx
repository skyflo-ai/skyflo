"use client";

import React, { useEffect, useState } from "react";
import { getMetrics } from "@/lib/api";
import MetricCard from "./MetricCard";
import TokenUsageChart from "./TokenUsageChart";
import CostTrendChart from "./CostTrendChart";
import TimetoFirstTokenAreaChart from "./TimetoFirstTokenAreaChart";
import CacheEfficiencyGauge from "./CacheEfficiencyGauge";
import { motion } from "framer-motion";
import {
  MdOutlineChatBubbleOutline,
  MdOutlineAttachMoney,
  MdOutlineSwapVert,
  MdOutlineThumbUpOffAlt,
  MdOutlineRequestQuote,
} from "react-icons/md";
import { MetricsAggregation } from "@/types/analytics";
import TotalResponseTimeAreaChart from "./TotalResponseTimeAreaChart";
import TimeRangeDropdown, {
  AnalyticsTimeFilter,
  QuickRangeKey,
  QuickRangeOption,
  QUICK_RANGES,
} from "./TimeRangeDropdown";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6 h-full w-full overflow-auto p-6">
      <div className="flex justify-between items-start">
        <div className="space-y-2.5">
          <div className="h-5 w-24 bg-zinc-800/40 rounded-md animate-pulse" />
          <div className="h-3.5 w-52 bg-zinc-800/20 rounded-md animate-pulse" />
        </div>
        <div className="h-8 w-48 bg-zinc-800/20 rounded-lg animate-pulse" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-24 bg-zinc-800/15 rounded-xl animate-pulse"
          />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 h-[380px] bg-zinc-800/15 rounded-xl animate-pulse" />
        <div className="lg:col-span-2 h-[380px] bg-zinc-800/15 rounded-xl animate-pulse" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-[320px] bg-zinc-800/15 rounded-xl animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}

export default function Analytics() {
  const STORAGE_KEY = "analytics_time_filter_v1";
  const defaultQuickRange = QUICK_RANGES.find((range) => range.key === "24h")!;

  const buildQuickRangeFilter = (range: QuickRangeOption): AnalyticsTimeFilter => {
    const endAt = new Date();
    const startAt = new Date(endAt);
    if (range.unit === "minutes") {
      startAt.setMinutes(startAt.getMinutes() - range.amount);
    } else if (range.unit === "hours") {
      startAt.setHours(startAt.getHours() - range.amount);
    } else {
      startAt.setDate(startAt.getDate() - range.amount);
    }

    return {
      kind: "quick",
      quickRangeKey: range.key,
      quickRangeLabel: range.label,
      startAt: startAt.toISOString(),
      endAt: endAt.toISOString(),
      timezone: "UTC",
    };
  };

  const getQuickRangeFromKey = (key: QuickRangeKey): QuickRangeOption | null => {
    return QUICK_RANGES.find((range) => range.key === key) ?? null;
  };

  const [selectedFilter, setSelectedFilter] = useState<AnalyticsTimeFilter>(() => {
    if (typeof window !== "undefined") {
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as AnalyticsTimeFilter;
          if (parsed.kind === "quick" && parsed.quickRangeKey) {
            const quickRange = getQuickRangeFromKey(parsed.quickRangeKey);
            if (quickRange) {
              return buildQuickRangeFilter(quickRange);
            }
          } else if (parsed.kind === "custom" && parsed.startAt && parsed.endAt) {
            return {
              kind: "custom",
              startAt: parsed.startAt,
              endAt: parsed.endAt,
              timezone: "UTC",
            };
          }
        }
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
    return buildQuickRangeFilter(defaultQuickRange);
  });
  const [data, setData] = useState<MetricsAggregation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const persistFilter = (filter: AnalyticsTimeFilter) => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(filter));
  };

  const handleQuickRangeChange = (range: QuickRangeOption) => {
    const nextFilter = buildQuickRangeFilter(range);
    setSelectedFilter(nextFilter);
    persistFilter(nextFilter);
  };

  const handleCustomRangeApply = (
    startAt: string,
    endAt: string,
    timezone: "UTC",
  ) => {
    const nextFilter: AnalyticsTimeFilter = {
      kind: "custom",
      startAt,
      endAt,
      timezone,
    };
    setSelectedFilter(nextFilter);
    persistFilter(nextFilter);
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getMetrics({
          startDateTime: new Date(selectedFilter.startAt),
          endDateTime: new Date(selectedFilter.endAt),
        });
        setData(result);
      } catch {
        setError("Failed to load analytics data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedFilter.startAt, selectedFilter.endAt]);

  if (loading && !data) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-sm text-zinc-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-3 text-xs text-sky-400 hover:text-sky-300 transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const rate = data?.approval_acceptance_rate;
  const percentage = rate != null ? Math.round(rate * 100) : null;

  const getApprovalRateColor = (pct: number | null): string | undefined => {
    if (pct == null) return undefined;
    if (pct < 50) return "text-rose-400";
    if (pct < 60) return "text-orange-400";
    if (pct < 70) return "text-amber-400";
    if (pct < 80) return "text-yellow-400";
    if (pct < 90) return "text-lime-400";
    return "text-emerald-400";
  };

  return (
    <div className="flex flex-col gap-6 h-full w-full overflow-auto p-6">
      <div className="flex max-sm:flex-col max-sm:gap-4 justify-between items-start">
        <div>
          <h1 className="text-lg font-semibold text-white tracking-tight">
            Analytics
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Usage, performance, and cost insights
          </p>
        </div>
        <div className="flex items-center gap-3 max-sm:w-full">
          <TimeRangeDropdown
            value={selectedFilter}
            onQuickRangeSelect={handleQuickRangeChange}
            onCustomRangeApply={handleCustomRangeApply}
          />
        </div>
      </div>

      {data && (
        <>
          <motion.div
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            <MetricCard
              title="Conversations"
              value={`${data.total_conversations}`}
              icon={<MdOutlineChatBubbleOutline />}
            />
            <MetricCard
              title="Total Cost"
              value={`$${data.total_cost.toFixed(4)}`}
              icon={<MdOutlineAttachMoney />}
            />
            <MetricCard
              title="Total Tokens"
              value={data.total_tokens.toLocaleString()}
              icon={<MdOutlineSwapVert />}
            />
            <MetricCard
              title="Approval Rate"
              value={percentage != null ? `${percentage}%` : "N/A"}
              icon={<MdOutlineThumbUpOffAlt />}
              valueColor={getApprovalRateColor(percentage)}
            />
            <MetricCard
              title="Avg. Cost / Conversation"
              value={`$${data.avg_cost_per_conversation.toFixed(2)}`}
              icon={<MdOutlineRequestQuote />}
            />
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-6">
              <h3 className="text-sm font-medium text-zinc-300 mb-5">
                Token Usage
              </h3>
              <TokenUsageChart data={data.daily_breakdown} />
            </div>
            <div className="lg:col-span-2 rounded-xl bg-white/[0.03] border border-white/[0.06] p-6 flex flex-col">
              <h3 className="text-sm font-medium text-zinc-300 mb-2">
                Cache Efficiency
              </h3>
              <div className="flex-1 min-h-0">
                <CacheEfficiencyGauge hitRate={data.cache_hit_rate} />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pb-2">
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-6">
              <h3 className="text-sm font-medium text-zinc-300 mb-5">
                Cost Over Time
              </h3>
              <CostTrendChart data={data.daily_breakdown} />
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-6">
              <h3 className="text-sm font-medium text-zinc-300 mb-5">
                Time to First Token
              </h3>
              <TimetoFirstTokenAreaChart data={data.daily_breakdown} />
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-6">
              <h3 className="text-sm font-medium text-zinc-300 mb-5">
                Total Response Time
              </h3>
              <TotalResponseTimeAreaChart data={data.daily_breakdown} />
            </div>
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="flex items-center justify-center h-64">
          <p className="text-sm text-zinc-500">
            No analytics data found for the selected date range.
          </p>
        </div>
      )}
    </div>
  );
}
