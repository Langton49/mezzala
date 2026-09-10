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
        <div className="flex gap-4 border-b p-2">
            {
                TABS.map((tab) => (
                    <button key={tab.key} onClick={() => setCurrTab(tab.key)} className={currTab === tab.key ? "font-bold" : ""}>
                        {tab.label}
                    </button>
                ))
            }
        </div>
    )
}

