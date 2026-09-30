"use client";
import { createContext, useContext, useState, ReactNode } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

type Tab = "standings" | "fixtures" | "stats";
const TABS: Tab[] = ["standings", "fixtures", "stats"];

// Sentinel "league" selection meaning "every league at once" — used by the
// sidebar's "World Football" row and the by-date fixture view. Real bzzorio
// league ids are always positive, so 0 can't collide with a real one.
export const WORLD_FOOTBALL_ID = 0;

interface DashboardState {
  currLeague: number | null;
  setCurrLeague: (id: number | null) => void;
  currTab: Tab;
  setCurrTab: (tab: Tab) => void;
}

const DashboardContext = createContext<DashboardState | null>(null);

function parseLeague(value: string | null): number | null {
  if (value === null) return null;
  const n = Number(value);
  return Number.isInteger(n) ? n : null;
}

function parseTab(value: string | null): Tab {
  return (TABS as string[]).includes(value ?? "") ? (value as Tab) : "fixtures";
}

// League + tab live in the URL (?league=&tab=), not just in-memory state —
// a reload re-mounts this provider from scratch, and without the URL as the
// source of truth on first render, it always came back to the hardcoded
// null/"fixtures" defaults no matter what was selected before the reload.
export function DashboardProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [currLeague, setCurrLeagueState] = useState<number | null>(() => parseLeague(searchParams.get("league")));
  const [currTab, setCurrTabState] = useState<Tab>(() => parseTab(searchParams.get("tab")));

  // router.replace, not push — switching leagues/tabs shouldn't fill up
  // browser history with a back-button stop for every click.
  function syncUrl(league: number | null, tab: Tab) {
    const params = new URLSearchParams();
    if (league !== null) params.set("league", String(league));
    if (tab !== "fixtures") params.set("tab", tab); // "fixtures" is the default — omit it to keep the common-case URL clean
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function setCurrLeague(id: number | null) {
    setCurrLeagueState(id);
    syncUrl(id, currTab);
  }

  function setCurrTab(tab: Tab) {
    setCurrTabState(tab);
    syncUrl(currLeague, tab);
  }

  return (
    <DashboardContext.Provider
      value={{
        currLeague,
        setCurrLeague,
        currTab,
        setCurrTab,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboard has to be used in DashboardProvider");
  return context;
}
