"use client";

import { useEffect, useRef } from "react";
import { useSpring, useTransform, motion } from "framer-motion";

interface AnimatedCounterProps {
    value: string;
    className?: string;
}

export function AnimatedCounter({ value, className }: AnimatedCounterProps) {
    const match = value.match(/^([^0-9\.-]*)([\d,\.]+)([^0-9\.]*)$/);

    if (!match) {
        return <span className={className}>{value}</span>;
    }

    const prefix = match[1];
    const numericPart = match[2];
    const suffix = match[3];

    const parsedValue = parseFloat(numericPart.replace(/,/g, ""));

    if (isNaN(parsedValue)) {
        return <span className={className}>{value}</span>;
    }

    const count = useSpring(0, {
        stiffness: 100,
        damping: 20,
        duration: 0.5
    });

    useEffect(() => {
        count.set(parsedValue);
    }, [parsedValue, count]);
    const rounded = useTransform(count, (latest) => {
        const hasDecimal = numericPart.includes(".");
        const decimalPlaces = hasDecimal ? numericPart.split(".")[1].length : 0;

        let formattedNumber = latest.toFixed(decimalPlaces);

        const parts = formattedNumber.split(".");
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        formattedNumber = parts.join(".");

        return `${prefix}${formattedNumber}${suffix}`;
    });

    return (
        <motion.span className={className}>{rounded}</motion.span>
    );
}
