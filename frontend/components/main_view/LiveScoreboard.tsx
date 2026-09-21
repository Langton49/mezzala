"use client";
import { useLiveScores } from "@/hooks/useLiveScores";
import { MatchRow } from "./MatchRow";

export function LiveScoreboard() {
  const matches = useLiveScores();

  if (matches.length === 0) {
    return <div className="p-8 text-center text-sm text-muted-foreground">No live matches right now.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      {matches.map((match) => (
        <MatchRow key={match.id} match={match} />
      ))}
    </div>
  );
}
