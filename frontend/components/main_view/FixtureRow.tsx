import { Fixture } from "@/lib/types";
import { Logo } from "@/components/common/Logo";
import { StatusPill } from "@/components/common/StatusPill";
import { Skeleton } from "@/components/common/Skeleton";

export function FixtureRow({ fixture }: { fixture: Fixture }) {
  return (
    <div className="flex items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-b-0 hover:bg-muted">
      <div className="w-14 shrink-0">
        <StatusPill status={fixture.status} eventDate={fixture.event_date} />
      </div>

      <div className="flex flex-1 items-center justify-end gap-2 text-right text-sm">
        <span className="truncate">{fixture.home_team}</span>
        <Logo id={fixture.home_team_id} kind="team" alt={fixture.home_team} size={20} />
      </div>

      <div className="flex w-14 shrink-0 items-center justify-center gap-1 text-sm font-semibold tabular-nums">
        <span>{fixture.home_score ?? "-"}</span>
        <span className="text-muted-foreground">:</span>
        <span>{fixture.away_score ?? "-"}</span>
      </div>

      <div className="flex flex-1 items-center gap-2 text-left text-sm">
        <Logo id={fixture.away_team_id} kind="team" alt={fixture.away_team} size={20} />
        <span className="truncate">{fixture.away_team}</span>
      </div>
    </div>
  );
}

export function FixtureRowSkeleton() {
  return (
    <div className="flex items-center gap-3 border-b border-border px-4 py-3 last:border-b-0">
      <Skeleton className="h-3 w-10" />
      <div className="flex flex-1 items-center justify-end gap-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
      <Skeleton className="h-4 w-10" />
      <div className="flex flex-1 items-center gap-2">
        <Skeleton className="h-5 w-5 rounded-full" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  );
}

export function FixtureListSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      {Array.from({ length: rows }).map((_, i) => (
        <FixtureRowSkeleton key={i} />
      ))}
    </div>
  );
}
