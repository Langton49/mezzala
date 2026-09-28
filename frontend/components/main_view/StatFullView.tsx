"use client";
import { useEffect, useState } from "react";
import { PlayerStat } from "@/lib/types";
import { PlayerStatRow, PlayerStatRowSkeleton } from "./PlayerStatRow";
import { STAT_META, StatType } from "./PlayerStatsView";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const FULL_SIZE = 20;

export function StatFullView({
  leagueId,
  statType,
  onBack,
}: {
  leagueId: number;
  statType: StatType;
  onBack: () => void;
}) {
  const [stats, setStats] = useState<PlayerStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/stats/${leagueId}/${statType}`)
      .then((res) => res.json())
      .then(setStats)
      .catch(() => setStats([]))
      .finally(() => setLoading(false));
  }, [leagueId, statType]);

  const meta = STAT_META[statType];
  const top = stats.slice(0, FULL_SIZE);

  return (
    <div>
      <button
        onClick={onBack}
        className="mb-3 text-sm font-medium text-primary transition-colors hover:text-primary-strong"
      >
        ← Back
      </button>
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold">{meta.title}</h3>
        </div>
        {loading && Array.from({ length: 10 }).map((_, i) => <PlayerStatRowSkeleton key={i} />)}
        {!loading && top.length === 0 && (
          <div className="p-6 text-center text-sm text-muted-foreground">No data available.</div>
        )}
        {!loading && top.map((s) => <PlayerStatRow key={s.player_id} stat={s} valueLabel={meta.short} />)}
      </div>
    </div>
  );
}
