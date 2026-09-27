"use client";
import { useState } from "react";
import { useDashboard } from "@/context/DashboardContext";
import { MatchdayView } from "./MatchdayView";
import { DateView } from "./DateView";

type ViewMode = "matchday" | "date";

export function FixturesView({ leagueId }: { leagueId: number | null }) {
  const [mode, setMode] = useState<ViewMode>("matchday");
  const { setCurrLeague } = useDashboard();

  // The date view always shows every league's fixtures for that day, never
  // just the sidebar's selected league. Leaving that league highlighted
  // while viewing it reads as if the results were scoped to it, so clear
  // the selection on switching in.
  function switchToDate() {
    setCurrLeague(null);
    setMode("date");
  }

  return (
    <div>
      <div className="mb-4 flex gap-1 border-b border-border">
        <ModeTab label="Matchdays" active={mode === "matchday"} onClick={() => setMode("matchday")} />
        <ModeTab label="By date" active={mode === "date"} onClick={switchToDate} />
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
