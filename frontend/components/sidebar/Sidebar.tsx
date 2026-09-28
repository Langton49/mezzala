"use client";

import Image from "next/image";
import { useDashboard } from "@/context/DashboardContext";
import { CollapseToggle } from "./CollapseToggle";
import { LeagueList } from "./LeagueList";

export function Sidebar(){
    const {sidebarCollapsed} = useDashboard();
    return(
        <aside
            className={`flex flex-col border-r border-border bg-card py-2 transition-[width] duration-200 ${
                sidebarCollapsed ? "w-12" : "w-52"
            }`}
        >
            <div className={`mb-4 flex items-center ${sidebarCollapsed ? "flex-col gap-1.5 px-1" : "justify-between pl-5 pr-2.5"}`}>
                {sidebarCollapsed ? (
                    <Image src="/MiniLogo.png" alt="Mezzala" width={412} height={455} className="h-6 w-auto" priority />
                ) : (
                    <Image src="/FullLogo.png" alt="Mezzala" width={919} height={238} className="h-6 w-auto" priority />
                )}
                <CollapseToggle/>
            </div>
            <LeagueList collapsed={sidebarCollapsed} />
        </aside>
    )
}
