"use client";

import React from "react";
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

    ];

    return (
        <div className="flex bg-dark-card border max-lg:flex-col items-center border-white/10 rounded-lg p-1 gap-1">
            <div className="flex gap-1">
                {ranges.map((range) => (
                    <Button
                        key={range.value}
                        variant={selectedRange === range.value ? "default" : "ghost"}
                        onClick={() => onRangeChange(range.value)}
                        className={`h-8 px-4 text-sm font-medium transition-all duration-200 ${selectedRange === range.value
                            ? "shadow-lg text-blue-400 bg-blue-400/5"
                            : " hover:text-blue-400 hover:bg-blue-400/5 duration-300"
                            }`}
                    >
                        {range.label}
                    </Button>
                ))}
            </div>
            <div>

                <Button
                    key={"custom"}
                    variant={selectedRange === "custom" ? "default" : "ghost"}
                    onClick={() => onRangeChange("custom")}
                    className={`h-8 px-4 text-sm font-medium transition-all duration-200 ${selectedRange === "custom"
                        ? "shadow-lg text-blue-400 bg-blue-400/5"
                        : " hover:text-blue-400 hover:bg-blue-400/5 duration-300"
                        }`}
                >
                    {"Custom"}
                </Button>

            </div>

        </div>
    );
}
