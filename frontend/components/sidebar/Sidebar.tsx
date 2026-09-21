"use client";

import { useDashboard } from "@/context/DashboardContext";
import { CollapseToggle } from "./CollapseToggle";
import { LeagueList } from "./LeagueList";

export function Sidebar(){
    const {sidebarCollapsed} = useDashboard();
    return(
        <aside
            className={`flex flex-col border-r border-border bg-card py-2 transition-[width] duration-200 ${
                sidebarCollapsed ? "w-12" : "w-56"
            }`}
        >
            <CollapseToggle/>
            {!sidebarCollapsed && <LeagueList />}
        </aside>
    )
}
