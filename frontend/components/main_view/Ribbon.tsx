"use client";

import { useDashboard } from "@/context/DashboardContext";
import { TabBar } from "@/components/common/TabBar";

const TABS = [
  { key: "standings", label: "Standings" },
  { key: "fixtures", label: "Fixtures" },
  { key: "stats", label: "Statistics" },
] as const;

export function Ribbon() {
  const { currTab, setCurrTab } = useDashboard();
  return <TabBar tabs={TABS} active={currTab} onChange={setCurrTab} />;
}
