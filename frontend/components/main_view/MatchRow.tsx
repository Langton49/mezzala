import { Match } from "@/lib/types";
import { Logo } from "@/components/common/Logo";
import { StatusPill } from "@/components/common/StatusPill";

export function MatchRow({ match }: { match: Match }) {
  return (
    <div className="flex items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-b-0 hover:bg-muted">
      <div className="w-14 shrink-0">
        <StatusPill status={match.status} eventDate={match.event_date} currentMinute={match.current_minute} />
      </div>

      <div className="flex flex-1 items-center justify-end gap-2 text-right text-sm">
        <span className="truncate">{match.home_team}</span>
        <Logo id={match.home_team_id} kind="team" alt={match.home_team} size={20} />
      </div>

      <div className="flex w-14 shrink-0 items-center justify-center gap-1 text-sm font-semibold tabular-nums">
        <span>{match.home_score ?? "-"}</span>
        <span className="text-muted-foreground">:</span>
        <span>{match.away_score ?? "-"}</span>
      </div>

      <div className="flex flex-1 items-center gap-2 text-left text-sm">
        <Logo id={match.away_team_id} kind="team" alt={match.away_team} size={20} />
        <span className="truncate">{match.away_team}</span>
      </div>
    </div>
  );
}
