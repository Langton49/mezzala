"use client";
import { useLiveScores } from "@/hooks/useLiveScores";
import { MatchRow } from "./MatchRow";

export function LiveScoreboard() {
  const matches = useLiveScores();

  if (matches.length === 0) {
    return <div className="p-6 text-sm text-gray-500">No live matches right now.</div>;
  }

  return (
    <div className="rounded border border-gray-200">
      {matches.map((match) => (
        <MatchRow key={match.match_id} match={match} />
      ))}
    </div>
  );
}