import { PlayerStat } from "@/lib/types";
import { Logo } from "@/components/common/Logo";
import { Skeleton } from "@/components/common/Skeleton";

const POSITION_LABELS: Record<string, string> = {
  G: "Goalkeeper",
  D: "Defender",
  M: "Midfielder",
  F: "Forward",
};

function positionLabel(code: string | null): string | null {
  if (!code) return null;
  return POSITION_LABELS[code] ?? code;
}

export function PlayerStatRow({ stat, valueLabel }: { stat: PlayerStat; valueLabel: string }) {
  const position = positionLabel(stat.player_position);
  return (
    <div className="flex items-center gap-2.5 border-b border-border px-3 py-2 transition-colors last:border-b-0 hover:bg-muted">
      <span className="w-4 shrink-0 text-sm tabular-nums text-muted-foreground">{stat.rank}</span>
      <Logo id={stat.player_id} kind="player" alt={stat.player_name} size={24} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm">{stat.player_name}</div>
        <div className="truncate text-xs text-muted-foreground">
          {stat.team_name}
          {position ? ` · ${position}` : ""}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <div className="text-sm font-semibold tabular-nums">{stat.value}</div>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{valueLabel}</div>
      </div>
    </div>
  );
}

export function PlayerStatRowSkeleton() {
  return (
    <div className="flex items-center gap-2.5 border-b border-border px-3 py-2 last:border-b-0">
      <Skeleton className="h-3 w-4" />
      <Skeleton className="h-6 w-6 rounded-full" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-2.5 w-20" />
      </div>
      <Skeleton className="h-3 w-8" />
    </div>
  );
}
