"use client";
import { useState } from "react";
import { MatchdayView } from "./MatchdayView";
import { DateView } from "./DateView";

type ViewMode = "matchday" | "date";

export function FixturesView({ leagueId }: { leagueId: number | null }) {
  const [mode, setMode] = useState<ViewMode>("matchday");

  return (
    <div>
      <div>
        <button onClick={() => setMode("matchday")}>Matchdays</button>
        <button onClick={() => setMode("date")}>Dates</button>
      </div>
      {mode === "matchday" && <MatchdayView leagueId={leagueId} />}
      {mode === "date" && <DateView />}
    </div>
  );
}
