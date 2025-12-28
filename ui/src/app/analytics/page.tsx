"use client";

import Analytics from "@/components/analytics/Analytics";
import Navbar from "@/components/navbar/Navbar";

export default function AnalyticsPage() {
    return (
        <div className="flex h-screen w-full bg-background">
            <Navbar />
            <div className="flex-grow p-6 overflow-y-auto">
                <Analytics />
            </div>
        </div>
    );
}
