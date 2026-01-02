"use client";

import React, { useEffect, useState } from "react";
import { getMetrics } from "@/lib/api";
import MetricCard from "./MetricCard";
import TimeRangeSelector from "./TimeRangeSelector";
import TokenUsageChart from "./TokenUsageChart";
import CostTrendChart from "./CostTrendChart";
import LatencyChart from "./LatencyChart";
import CacheEfficiencyGauge from "./CacheEfficiencyGauge";
import { motion } from "framer-motion";
import { type DateRange } from "react-day-picker"
import { Button } from "../ui/button";
import { DatePickerWithRange } from "./DatePickerWithRange";
import { MdOutlineAttachMoney } from "react-icons/md";
import { MdOutlineChatBubbleOutline } from "react-icons/md";
import { MdOutlineThumbUpOffAlt } from "react-icons/md";
import { MdOutlineSwapVert } from "react-icons/md";
import { MetricsAggregation } from "@/types/analytics";

export default function Analytics() {
    const [timeRange, setTimeRange] = useState<number | "custom">(30);
    const [dateRange, setDateRange] = useState<DateRange | undefined>(undefined);
    const [data, setData] = useState<MetricsAggregation | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                let result;
                if (timeRange === "custom") {
                    if (dateRange?.from && dateRange?.to) {
                        result = await getMetrics({
                            startDate: dateRange.from,
                            endDate: dateRange.to
                        });
                    } else {
                        // Waiting for full range selection
                        setLoading(false);
                        return;
                    }
                } else {
                    result = await getMetrics(timeRange);
                }
                setData(result);
            } catch (err) {
                setError("Failed to load analytics data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [timeRange, dateRange]);

    if (loading && !data) {
        return (
            <div className="flex items-center justify-center h-full text-text-secondary">
                Loading analytics...
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-full text-red-500">
                {error}
            </div>
        );
    }

    // If we are in custom mode and waiting for data, show empty or previous data?
    // Let's show data if available, or loading.

    // If no data yet (e.g. custom mode selected but no dates), show prompt?
    // Or just empty state.

    const displayData = data;

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
    };

    return (
        <div className="flex flex-col gap-5 h-full overflow-y-auto max-sm:p-2 p-8 bg-dark-bg text-text-primary">

            <div className="bg-gradient-to-br from-blue-600/10 to-transparent rounded-xl backdrop-blur-md shadow-lg shadow-blue-900/10 mb-8">
                <div className="flex  max-sm:flex-col max-sm:gap-10 justify-between bg-gradient-to-br from-blue-600/10 to-transparent rounded-xl p-8">
                    <div className="max-sm:text-center">
                        <h1 className="text-3xl max-sm:inline-block font-bold bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-400 bg-clip-text text-transparent tracking-tight flex items-center">
                            Analytics
                        </h1>

                        <p className="text-slate-400 mt-2 sm:text-left">
                            Overview of your AI usage and performance
                        </p>
                    </div>

                    <div className="flex flex-row max-lg:flex-col-reverse items-center gap-4">
                        {timeRange === "custom" && (
                            <DatePickerWithRange date={dateRange} setDate={setDateRange} />
                        )}
                        <TimeRangeSelector selectedRange={timeRange} onRangeChange={setTimeRange} />
                    </div>

                </div>
            </div>

            {displayData && (
                <div>
                    <motion.div
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                    >
                        <MetricCard
                            title="Total Cost"
                            value={`$${displayData.total_cost.toFixed(4)}`}
                            trend={null}
                            icon={<MdOutlineAttachMoney />}
                            color="text-green-400"
                        />
                        <MetricCard
                            title="Total Tokens"
                            value={displayData.total_tokens.toLocaleString()}
                            trend={null}
                            icon={<MdOutlineSwapVert />}
                            color="text-blue-400"
                        />
                        <MetricCard
                            title="Tool Approval Acceptance Rate"
                            value={displayData.approval_acceptance_rate ? `${Math.round(displayData.approval_acceptance_rate * 100)}%` : "N/A"}
                            trend={null}
                            icon={<MdOutlineThumbUpOffAlt />}
                            color="text-yellow-400"
                        />
                        <MetricCard
                            title="Conversations"
                            value={displayData.total_conversations.toLocaleString()}
                            trend={null}
                            icon={<MdOutlineChatBubbleOutline />}
                            color="text-purple-400"
                        />
                    </motion.div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                        <div className="lg:col-span-2 bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 text-text-primary">Token Usage Trend</h3>
                            <TokenUsageChart data={displayData.daily_breakdown} />
                        </div>
                        <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 max-sm:p-2 shadow-lg flex flex-col items-center justify-center">
                            <h3 className="text-xl font-semibold mb-4 text-text-primary w-full text-left">Cache Efficiency</h3>
                            <CacheEfficiencyGauge hitRate={displayData.cache_hit_rate} />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-8">
                        <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 text-text-primary">Cost Over Time</h3>
                            <CostTrendChart data={displayData.daily_breakdown} />
                        </div>
                        <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 text-text-primary">Latency Performance</h3>
                            <LatencyChart data={displayData.daily_breakdown} />
                        </div>
                    </div>
                </div>
            )}

            {!displayData && !loading && (
                <div className="flex items-center justify-center h-64 text-text-secondary">
                    Select a date range to view analytics.
                </div>
            )}
        </div>
    );
}
