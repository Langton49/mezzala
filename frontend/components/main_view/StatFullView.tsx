"use client";
import { PlayerStat } from "@/lib/types";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { Panel, EmptyState, ErrorState } from "@/components/common/Panel";
import { PlayerStatRow, PlayerStatRowSkeleton } from "./PlayerStatRow";
import { STAT_META, StatType } from "./PlayerStatsView";

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
  const { data: stats, loading, error } = useJsonFetch<PlayerStat[]>(`/stats/${leagueId}/${statType}`);
  const meta = STAT_META[statType];
  const top = stats?.slice(0, FULL_SIZE) ?? [];

  return (
    <div>
      <button
        onClick={onBack}
        className="mb-2.5 text-sm font-medium text-primary transition-colors hover:text-primary-strong"
      >
        ← Back
      </button>
      <Panel>
        <div className="border-b border-border px-3 py-2">
          <h3 className="text-sm font-semibold">{meta.title}</h3>
        </div>
        {loading && Array.from({ length: 10 }).map((_, i) => <PlayerStatRowSkeleton key={i} />)}
        {!loading && top.length === 0 && (error ? <ErrorState>Couldn&apos;t load stats.</ErrorState> : <EmptyState>No data available.</EmptyState>)}
        {!loading && top.map((s) => <PlayerStatRow key={s.player_id} stat={s} valueLabel={meta.short} />)}
      </Panel>
    </div>
  );
}
