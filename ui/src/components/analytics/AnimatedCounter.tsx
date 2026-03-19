"use client";

import { useEffect } from "react";
import { useSpring, useTransform, motion } from "framer-motion";

interface AnimatedCounterProps {
    value: string;
    className?: string;
}

export function AnimatedCounter({ value, className }: AnimatedCounterProps) {
    const count = useSpring(0, {
        stiffness: 100,
        damping: 20,
    });

    const match = value.match(/^([^0-9\.-]*)([\d,\.]+)([^0-9\.]*)$/);
    const prefix = match?.[1] || "";
    const numericPart = match?.[2] || value;
    const suffix = match?.[3] || "";
    const parsedValue = parseFloat(numericPart.replace(/,/g, ""));

    const rounded = useTransform(count, (latest) => {
        if (!match || isNaN(parsedValue)) {
            return value;
        }
        
        const hasDecimal = numericPart.includes(".");
        const decimalPlaces = hasDecimal ? numericPart.split(".")[1].length : 0;

        let formattedNumber = latest.toFixed(decimalPlaces);

        const parts = formattedNumber.split(".");
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        formattedNumber = parts.join(".");

        return `${prefix}${formattedNumber}${suffix}`;
    });

    useEffect(() => {
        if (match && !isNaN(parsedValue)) {
            count.set(parsedValue);
        }
    }, [parsedValue, count]);

    if (!match || isNaN(parsedValue)) {
        return <span className={className}>{value}</span>;
    }

    return (
        <motion.span className={className}>{rounded}</motion.span>
    );
}
