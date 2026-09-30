"use client";
import { PlayerStat } from "@/lib/types";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { Panel, EmptyState, ErrorState } from "@/components/common/Panel";
import { PlayerStatRow, PlayerStatRowSkeleton } from "./PlayerStatRow";
import { STAT_META, StatType } from "./PlayerStatsView";

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
  const { data: stats, loading, error } = useJsonFetch<PlayerStat[]>(`/stats/${leagueId}/${statType}`);
  const top = stats?.slice(0, CARD_SIZE) ?? [];
  const meta = STAT_META[statType];

  return (
    <Panel>
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
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
        {!loading && top.length === 0 && (error ? <ErrorState>Couldn&apos;t load stats.</ErrorState> : <EmptyState>No data available.</EmptyState>)}
        {!loading && top.map((s) => <PlayerStatRow key={s.player_id} stat={s} valueLabel={meta.short} />)}
      </div>
    </Panel>
  );
}
