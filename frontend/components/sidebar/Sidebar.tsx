"use client";

import { useDashboard } from "@/context/DashboardContext";
import { CollapseToggle } from "./CollapseToggle";
import { LeagueList } from "./LeagueList";

export function Sidebar(){
    const {sidebarCollapsed} = useDashboard();
    return(
<aside className={sidebarCollapsed ? "w-12" : "w-56"}>
    <CollapseToggle/>
    {!sidebarCollapsed && <LeagueList />}

</aside>
    )
}