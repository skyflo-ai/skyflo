"use client";

import Analytics from "@/components/analytics/Analytics";
import Navbar from "@/components/navbar/Navbar";

export default function AnalyticsPage() {
    return (
        <div className="flex h-screen w-full bg-background">
            <Navbar />
            <div className="flex-grow overflow-y-auto p-4">
                <Analytics />
            </div>
        </div>
    );
}
