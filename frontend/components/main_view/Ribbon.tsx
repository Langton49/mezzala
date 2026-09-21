"use client";

import { useDashboard } from "@/context/DashboardContext";

const TABS = [
    {key: "standings", label: "Standings"},
    {key: "fixtures", label: "Fixtures"},
    {key: "stats", label: "Statistics"}
] as const;

export function Ribbon(){
    const {currTab, setCurrTab} = useDashboard();

    return (
        <div className="flex gap-1 border-b border-border bg-card px-2">
            {
                TABS.map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setCurrTab(tab.key)}
                        className={`-mb-px border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
                            currTab === tab.key
                                ? "border-primary text-primary"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        {tab.label}
                    </button>
                ))
            }
        </div>
    )
}
