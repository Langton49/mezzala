import { Match } from "@/lib/types";

export function MatchRow({ match }: { match: Match }) {
  const isLive = match.status === "live";

  return (
    <div className="flex items-center gap-4 border-b border-gray-200 px-4 py-3">
      <div className="w-14 shrink-0 text-sm text-gray-500">
        {isLive ? `${match.current_minute}'` : match.status}
      </div>
      <div className="flex-1 text-sm">{match.home_team}</div>
      <div className="w-6 text-right font-semibold">{match.home_score ?? "-"}</div>
      <div className="px-1 text-gray-400">:</div>
      <div className="w-6 font-semibold">{match.away_score ?? "-"}</div>
      <div className="flex-1 text-sm text-right">{match.away_team}</div>
    </div>
  );
}