"use client";

import { useEffect, useRef } from "react";
import { useSpring, useTransform, motion } from "framer-motion";

interface AnimatedCounterProps {
    value: string;
    className?: string;
}

export function AnimatedCounter({ value, className }: AnimatedCounterProps) {
    // Regex to separate prefix, number, and suffix
    // Examples: "$1,234.56" -> prefix="$", number="1234.56", suffix=""
    // "50%" -> prefix="", number="50", suffix="%"
    const match = value.match(/^([^0-9\.-]*)([\d,\.]+)([^0-9\.]*)$/);

    if (!match) {
        // Fallback for non-numeric strings
        return <span className={className}>{value}</span>;
    }

    const prefix = match[1];
    const numericPart = match[2];
    const suffix = match[3];

    // Remove commas for parsing
    const parsedValue = parseFloat(numericPart.replace(/,/g, ""));

    // Check if it's a valid number
    if (isNaN(parsedValue)) {
        return <span className={className}>{value}</span>;
    }

    // Create a spring value starting at 0
    const count = useSpring(0, {
        stiffness: 100,
        damping: 20,
        duration: 0.5
    });

    // Update the spring target when parsedValue changes
    useEffect(() => {
        count.set(parsedValue);
    }, [parsedValue, count]);

    // Transform the animated value back to a string
    const rounded = useTransform(count, (latest) => {
        // Format the number back to the original style (handling decimals if needed)
        // If original had decimals, keep them.
        const hasDecimal = numericPart.includes(".");
        const decimalPlaces = hasDecimal ? numericPart.split(".")[1].length : 0;

        let formattedNumber = latest.toFixed(decimalPlaces);

        // Add commas back
        // Using a simple regex to add commas
        const parts = formattedNumber.split(".");
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        formattedNumber = parts.join(".");

        return `${prefix}${formattedNumber}${suffix}`;
    });

    return (
        <motion.span className={className}>{rounded}</motion.span>
    );
}
