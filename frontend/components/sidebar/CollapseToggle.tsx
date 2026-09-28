"use client";
import { useDashboard } from "@/context/DashboardContext";

export function CollapseToggle() {
    const {sidebarCollapsed, toggleSidebar} = useDashboard();

    return (
        <button
            onClick={toggleSidebar}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
        >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className={`transition-transform duration-200 ${sidebarCollapsed ? "rotate-180" : ""}`}>
                <path d="M15 6l-6 6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        </button>
    )
}
