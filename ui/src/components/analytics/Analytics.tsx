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

interface DailyMetrics {
    date: string;
    cost: number;
    prompt_tokens: number;
    completion_tokens: number;
    cached_tokens: number;
    total_tokens: number;
    avg_ttft_ms: number | null;
    avg_ttr_ms: number | null;
    conversation_count: number;
}

interface MetricsAggregation {
    period_start: string;
    period_end: string;
    total_cost: number;
    total_tokens: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_cached_tokens: number;
    total_conversations: number;
    avg_ttft_ms: number | null;
    avg_ttr_ms: number | null;
    avg_cost_per_conversation: number;
    avg_tokens_per_conversation: number;
    cache_hit_rate: number;
    daily_breakdown: DailyMetrics[];
}

export default function Analytics() {
    const [timeRange, setTimeRange] = useState<number>(30);
    const [data, setData] = useState<MetricsAggregation | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await getMetrics(timeRange);
                setData(result);
            } catch (err) {
                setError("Failed to load analytics data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [timeRange]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full text-text-secondary">
                Loading analytics...
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="flex items-center justify-center h-full text-red-500">
                {error || "No data available"}
            </div>
        );
    }

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
    };

    return (
        <div className="flex flex-col h-full overflow-y-auto p-8 bg-dark-bg text-text-primary">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        Analytics
                    </h1>
                    <p className="text-text-secondary mt-1">
                        Overview of your AI usage and performance
                    </p>
                </div>
                <TimeRangeSelector selectedRange={timeRange} onRangeChange={setTimeRange} />
            </div>

            <motion.div
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
            >
                <MetricCard
                    title="Total Cost"
                    value={`$${data.total_cost.toFixed(4)}`}
                    trend={null}
                    icon="💰"
                    color="text-green-400"
                />
                <MetricCard
                    title="Total Tokens"
                    value={data.total_tokens.toLocaleString()}
                    trend={null}
                    icon="🔢"
                    color="text-blue-400"
                />
                <MetricCard
                    title="Avg Latency (TTR)"
                    value={data.avg_ttr_ms ? `${Math.round(data.avg_ttr_ms)}ms` : "N/A"}
                    trend={null}
                    icon="⚡"
                    color="text-yellow-400"
                />
                <MetricCard
                    title="Conversations"
                    value={data.total_conversations.toLocaleString()}
                    trend={null}
                    icon="💬"
                    color="text-purple-400"
                />
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                <div className="lg:col-span-2 bg-dark-card/50 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-semibold mb-4 text-text-primary">Token Usage Trend</h3>
                    <TokenUsageChart data={data.daily_breakdown} />
                </div>
                <div className="bg-dark-card/50 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-lg flex flex-col items-center justify-center">
                    <h3 className="text-xl font-semibold mb-4 text-text-primary w-full text-left">Cache Efficiency</h3>
                    <CacheEfficiencyGauge hitRate={data.cache_hit_rate} />
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-8">
                <div className="bg-dark-card/50 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-semibold mb-4 text-text-primary">Cost Over Time</h3>
                    <CostTrendChart data={data.daily_breakdown} />
                </div>
                <div className="bg-dark-card/50 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-semibold mb-4 text-text-primary">Latency Performance</h3>
                    <LatencyChart data={data.daily_breakdown} />
                </div>
            </div>
        </div>
    );
}
