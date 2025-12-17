"use client";

import Analytics from "@/components/analytics/Analytics";
import Navbar from "@/components/navbar/Navbar";

export default function AnalyticsPage() {
    return (
        <div className="flex bg-dark-bg min-h-screen">
            <Navbar />
            <div className="flex-grow flex flex-col h-screen overflow-hidden">
                <Analytics />
            </div>
        </div>
    );
}
