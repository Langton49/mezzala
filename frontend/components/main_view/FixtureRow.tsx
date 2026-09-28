import { Fixture } from "@/lib/types";
import { Logo } from "@/components/common/Logo";
import { StatusPill, LiveIndicator, formatKickoff, formatShortDate } from "@/components/common/StatusPill";
import { Skeleton } from "@/components/common/Skeleton";
import { Panel } from "@/components/common/Panel";

interface FixtureRowProps {
  fixture: Fixture;
  // A matchday's fixtures aren't all on the same calendar date, so the
  // matchday view opts into per-row dates; the by-date view already shows
  // one date for the whole list and doesn't need it repeated on every row.
  showDate?: boolean;
}

export function FixtureRow({ fixture, showDate = false }: FixtureRowProps) {
  const isLive = fixture.status === "live";
  const showTime = !isLive && fixture.status !== "finished";
  const dateTimeParts = [
    showDate ? formatShortDate(fixture.event_date) : null,
    showTime ? formatKickoff(fixture.event_date) : null,
  ].filter(Boolean);

  return (
    <div className="flex items-center gap-2.5 border-b border-border px-3 py-2 transition-colors last:border-b-0 hover:bg-muted">
      <div className="w-12 shrink-0">
        <StatusPill status={fixture.status} />
      </div>

      <div className="flex flex-1 items-center justify-end gap-2 text-right text-sm">
        <span className="truncate">{fixture.home_team}</span>
        <Logo id={fixture.home_team_id} kind="team" alt={fixture.home_team} size={20} />
      </div>

      <div className={`flex shrink-0 flex-col items-center justify-center ${showDate ? "w-22" : "w-12"}`}>
        <div className="flex items-center gap-1 text-sm font-semibold tabular-nums">
          <span>{fixture.home_score ?? "-"}</span>
          <span className="text-muted-foreground">:</span>
          <span>{fixture.away_score ?? "-"}</span>
        </div>
        {isLive ? (
          <LiveIndicator currentMinute={fixture.current_minute} className="text-[10px]" />
        ) : (
          dateTimeParts.length > 0 && (
            <span className="text-[10px] text-muted-foreground tabular-nums">{dateTimeParts.join(" · ")}</span>
          )
        )}
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
    <div className="flex items-center gap-2.5 border-b border-border px-3 py-2 last:border-b-0">
      <Skeleton className="h-3 w-8" />
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
    <Panel>
      {Array.from({ length: rows }).map((_, i) => (
        <FixtureRowSkeleton key={i} />
      ))}
    </Panel>
  );
}
