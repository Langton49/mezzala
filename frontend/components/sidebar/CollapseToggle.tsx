"use client";
import { useDashboard } from "@/context/DashboardContext";
import { use } from "react";

export function CollapseToggle() {
    const {sidebarCollapsed, toggleSidebar} = useDashboard();

    return (
        <button onClick={toggleSidebar} className="w-full p-2 text-left">
            {sidebarCollapsed ? "==>" : "X"}
        </button>
    )
}