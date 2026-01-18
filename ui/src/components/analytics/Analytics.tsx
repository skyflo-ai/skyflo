"use client";

import React, { useEffect, useState } from "react";
import { getMetrics } from "@/lib/api";
import MetricCard from "./MetricCard";
import TimeRangeSelector from "./TimeRangeSelector";
import TokenUsageChart from "./TokenUsageChart";
import CostTrendChart from "./CostTrendChart";
import TimetoFirstTokenAreaChart from "./TimetoFirstTokenAreaChart";
import CacheEfficiencyGauge from "./CacheEfficiencyGauge";
import { motion } from "framer-motion";
import { type DateRange } from "react-day-picker"
import { DatePickerWithRange } from "./DatePickerWithRange";
import { MdOutlineSwapVert, MdOutlineChatBubbleOutline, MdOutlineThumbUpOffAlt, MdOutlineAttachMoney, MdOutlineMoney } from "react-icons/md";
import { MetricsAggregation } from "@/types/analytics";
import TotalResponseTimeLineChart from "./TotalResponseTimeAreaChart";


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
                        // Normalize dates to UTC to avoid timezone issues when serializing
                        const fromDate = new Date(Date.UTC(
                            dateRange.from.getFullYear(),
                            dateRange.from.getMonth(),
                            dateRange.from.getDate()
                        ));

                        const toDate = new Date(Date.UTC(
                            dateRange.to.getFullYear(),
                            dateRange.to.getMonth(),
                            dateRange.to.getDate()
                        ));

                        result = await getMetrics({
                            startDate: fromDate,
                            endDate: toDate
                        });
                    } else {
                        // Waiting for full range selection
                        setLoading(false);
                        setData(null);
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
            <div className="flex items-center justify-center h-full ">
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

    const displayData = data;

    const rate = displayData?.approval_acceptance_rate;
    const percentage = rate != null ? Math.round(rate * 100) : null;

    const approvalAcceptanceRateColor =
        percentage === null
            ? "text-[#94a3b8]"
            : percentage < 50
                ? "text-[#ff7373]"
                : percentage < 60
                    ? "text-[#ff9257]"
                    : percentage < 70
                        ? "text-[#ffa55c]"
                        : percentage < 80
                            ? "text-[#fcde60]"
                            : percentage < 90
                                ? "text-[#c6ff6b]"
                                : "text-[#73ffa6]";

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
    };

    return (
        <div className="flex flex-col gap-5 h-full overflow-auto px-2 py-2 bg-dark">

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
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                    >
                        <MetricCard
                            title="Total Conversations"
                            value={`${displayData.total_conversations}`}
                            icon={<MdOutlineChatBubbleOutline />}
                            color=""
                        />

                        <MetricCard
                            title="Total Cost"
                            value={`$${displayData.total_cost.toFixed(4)}`}
                            icon={<MdOutlineAttachMoney />}
                            color="text-green-400"
                        />
                        <MetricCard
                            title="Total Tokens"
                            value={displayData.total_tokens.toLocaleString()}
                            icon={<MdOutlineSwapVert />}
                            color="text-blue-400"
                        />
                        <MetricCard
                            title="Tool Approval Acceptance Rate"
                            value={displayData.approval_acceptance_rate != null ? `${Math.round(displayData.approval_acceptance_rate * 100)}%` : "N/A"}
                            icon={<MdOutlineThumbUpOffAlt />}
                            color={approvalAcceptanceRateColor}
                        />
                        <MetricCard
                            title="Average Conversation Cost"
                            value={displayData.total_conversations > 0 ? `$${(displayData.total_cost / displayData.total_conversations).toFixed(2)}` : "$0.00"}
                            icon={<MdOutlineMoney />}
                            color="text-purple-400"
                        />
                    </motion.div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                        <div className="lg:col-span-2 bg-navbar rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 ">Token Usage Trend</h3>
                            <TokenUsageChart data={displayData.daily_breakdown} />
                        </div>
                        <div className="bg-navbar rounded-lg border border-slate-700/60 p-8 max-sm:p-2 shadow-lg flex flex-col items-center justify-center">
                            <h3 className="text-xl font-semibold mb-4  w-full text-left">Cache Efficiency</h3>
                            <CacheEfficiencyGauge hitRate={displayData.cache_hit_rate} />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-8">
                        <div className="bg-navbar rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 ">Cost Over Time</h3>
                            <CostTrendChart data={displayData.daily_breakdown} />
                        </div>
                        <div className="bg-navbar rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 ">Time To First Token (TTFT)</h3>
                            <TimetoFirstTokenAreaChart data={displayData.daily_breakdown} />
                        </div>
                        <div className="bg-navbar rounded-lg border border-slate-700/60 p-8 shadow-lg">
                            <h3 className="text-xl font-semibold mb-4 ">Total Response Time (TTR)</h3>
                            <TotalResponseTimeLineChart data={displayData.daily_breakdown} />
                        </div>
                    </div>
                </div>
            )}

            {!displayData && !loading && (
                <div className="flex items-center justify-center h-64">
                    Select a date range to view analytics.
                </div>
            )}
        </div>
    );
}
