"use client";
import { useState } from "react";
import { MatchdayView } from "./MatchdayView";
import { DateView } from "./DateView";

type ViewMode = "matchday" | "date";

export function FixturesView({ leagueId }: { leagueId: number | null }) {
  const [mode, setMode] = useState<ViewMode>("matchday");

  return (
    <div>
      <div className="mb-4 flex gap-1 border-b border-border">
        <ModeTab label="Matchdays" active={mode === "matchday"} onClick={() => setMode("matchday")} />
        <ModeTab label="By date" active={mode === "date"} onClick={() => setMode("date")} />
      </div>
      {mode === "matchday" && <MatchdayView leagueId={leagueId} />}
      {mode === "date" && <DateView />}
    </div>
  );
}

function ModeTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
        active ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
      }`}
    >
      {label}
    </button>
  );
}
