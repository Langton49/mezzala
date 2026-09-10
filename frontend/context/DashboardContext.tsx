"use client"
import { createContext, useContext, useState, ReactNode } from "react"

type Tab = "standings" | "fixtures" | "stats";

interface DashboardState {
    currLeague: number | null;
    setCurrLeague: (id: number | null) => void;
    currTab: Tab;
    setCurrTab: (tab: Tab) => void;
    sidebarCollapsed: boolean;
    toggleSidebar: ()=>void;
}

const DashboardContext = createContext<DashboardState | null>(null);

export function DashboardProvider({children}: {children: ReactNode}){
    const [currLeague, setCurrLeague] = useState<number | null>(null);
    const [currTab, setCurrTab] = useState<Tab>("fixtures");
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    return (
        <DashboardContext.Provider value={{
            currLeague,
            setCurrLeague,
            currTab,
            setCurrTab,
            sidebarCollapsed,
            toggleSidebar: () => setSidebarCollapsed((prev) => !prev)
        }} >
            {children}
        </DashboardContext.Provider>
    )
}

export function useDashboard(){
    const context = useContext(DashboardContext)
    if (!context) throw new Error("useDashboard has to be used in DashboardProvider");
    return context
}