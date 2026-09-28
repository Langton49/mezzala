"use client";
import { useState } from "react";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { EmptyState } from "@/components/common/Panel";
import { StatCard } from "./StatCard";
import { StatFullView } from "./StatFullView";

export const STAT_ORDER = ["scorers", "assists", "yellowcards", "redcards", "fouls"] as const;
export type StatType = (typeof STAT_ORDER)[number];

export const STAT_META: Record<StatType, { title: string; short: string }> = {
  scorers: { title: "Top Scorers", short: "Goals" },
  assists: { title: "Assists", short: "Assists" },
  yellowcards: { title: "Yellow Cards", short: "Yellow" },
  redcards: { title: "Red Cards", short: "Red" },
  fouls: { title: "Fouls", short: "Fouls" },
};

export function PlayerStatsView({ leagueId }: { leagueId: number | null }) {
  const [expanded, setExpanded] = useState<StatType | null>(null);

  if (leagueId === null) {
    return <EmptyState>Select a league to see statistics.</EmptyState>;
  }
  if (leagueId === WORLD_FOOTBALL_ID) {
    return <EmptyState>World Football doesn&apos;t have statistics — pick a specific league.</EmptyState>;
  }

  if (expanded) {
    return <StatFullView leagueId={leagueId} statType={expanded} onBack={() => setExpanded(null)} />;
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {STAT_ORDER.map((statType) => (
        <StatCard key={statType} leagueId={leagueId} statType={statType} onExpand={() => setExpanded(statType)} />
      ))}
    </div>
  );
}
