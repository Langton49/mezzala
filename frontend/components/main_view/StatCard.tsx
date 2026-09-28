"use client";
import { useEffect, useState } from "react";
import { PlayerStat } from "@/lib/types";
import { PlayerStatRow, PlayerStatRowSkeleton } from "./PlayerStatRow";
import { STAT_META, StatType } from "./PlayerStatsView";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const CARD_SIZE = 5;

export function StatCard({
  leagueId,
  statType,
  onExpand,
}: {
  leagueId: number;
  statType: StatType;
  onExpand: () => void;
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

  const top = stats.slice(0, CARD_SIZE);
  const meta = STAT_META[statType];

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold">{meta.title}</h3>
        <button
          onClick={onExpand}
          className="text-xs font-medium text-primary transition-colors hover:text-primary-strong"
        >
          See all →
        </button>
      </div>
      <div>
        {loading && Array.from({ length: CARD_SIZE }).map((_, i) => <PlayerStatRowSkeleton key={i} />)}
        {!loading && top.length === 0 && (
          <div className="p-6 text-center text-sm text-muted-foreground">No data available.</div>
        )}
        {!loading && top.map((s) => <PlayerStatRow key={s.player_id} stat={s} valueLabel={meta.short} />)}
      </div>
    </div>
  );
}
