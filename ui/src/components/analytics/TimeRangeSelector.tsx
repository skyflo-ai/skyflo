"use client";

import React from "react";

interface TimeRangeSelectorProps {
    selectedRange: number;
    onRangeChange: (range: number) => void;
}

export default function TimeRangeSelector({ selectedRange, onRangeChange }: TimeRangeSelectorProps) {
    const ranges = [
        { label: "7D", value: 7 },
        { label: "30D", value: 30 },
        { label: "90D", value: 90 },
    ];

    return (
        <div className="flex bg-dark-card border border-white/10 rounded-lg p-1">
            {ranges.map((range) => (
                <button
                    key={range.value}
                    onClick={() => onRangeChange(range.value)}
                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${selectedRange === range.value
                            ? "bg-primary text-white shadow-lg"
                            : "text-text-secondary hover:text-white hover:bg-white/5"
                        }`}
                >
                    {range.label}
                </button>
            ))}
        </div>
    );
}
