"use client";

import React from "react";

interface TimeRangeSelectorProps {
    selectedRange: number | "custom";
    onRangeChange: (range: number | "custom") => void;
}

import { Button } from "../ui/button";

interface TimeRangeSelectorProps {
    selectedRange: number | "custom";
    onRangeChange: (range: number | "custom") => void;
}

export default function TimeRangeSelector({ selectedRange, onRangeChange }: TimeRangeSelectorProps) {
    const ranges: { label: string; value: number | "custom" }[] = [
        { label: "7D", value: 7 },
        { label: "30D", value: 30 },
        { label: "90D", value: 90 },
        { label: "Custom", value: "custom" },
    ];

    return (
        <div className="flex bg-dark-card border border-white/10 rounded-lg p-1 gap-1">
            {ranges.map((range) => (
                <Button
                    key={range.value}
                    variant={selectedRange === range.value ? "default" : "ghost"}
                    onClick={() => onRangeChange(range.value)}
                    className={`h-8 px-4 text-sm font-medium transition-all duration-200 ${selectedRange === range.value
                            ? "shadow-lg"
                            : "text-text-secondary hover:text-white hover:bg-white/5"
                        }`}
                >
                    {range.label}
                </Button>
            ))}
        </div>
    );
}
