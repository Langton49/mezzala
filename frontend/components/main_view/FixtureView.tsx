"use client";
import { useState } from "react";
import { TabBar } from "@/components/common/TabBar";
import { MatchdayView } from "./MatchdayView";
import { DateView } from "./DateView";

const MODES = [
  { key: "matchday", label: "Matchdays" },
  { key: "date", label: "By date" },
] as const;
type ViewMode = (typeof MODES)[number]["key"];

export function FixturesView({ leagueId }: { leagueId: number | null }) {
  const [mode, setMode] = useState<ViewMode>("matchday");

  return (
    <div>
      <div className="mb-3">
        <TabBar tabs={MODES} active={mode} onChange={setMode} compact />
      </div>
      {mode === "matchday" && <MatchdayView leagueId={leagueId} />}
      {mode === "date" && <DateView leagueId={leagueId} />}
    </div>
  );
}
