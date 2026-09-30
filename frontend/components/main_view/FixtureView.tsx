"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useUrlParamSetter } from "@/hooks/useUrlParam";
import { TabBar } from "@/components/common/TabBar";
import { MatchdayView } from "./MatchdayView";
import { DateView } from "./DateView";

const MODES = [
  { key: "matchday", label: "Matchdays" },
  { key: "date", label: "By date" },
] as const;
type ViewMode = (typeof MODES)[number]["key"];

export function FixturesView({ leagueId }: { leagueId: number | null }) {
  const searchParams = useSearchParams();
  const setUrlParam = useUrlParamSetter();
  const [mode, setModeState] = useState<ViewMode>(() => (searchParams.get("view") === "date" ? "date" : "matchday"));

  function setMode(next: ViewMode) {
    setModeState(next);
    setUrlParam("view", next === "matchday" ? null : next); // matchday is the default — omit it from the URL
  }

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
