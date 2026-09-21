"use client";
import { useEffect, useState } from "react";
import { Fixture } from "@/lib/types";
import { FixtureRow, FixtureListSkeleton } from "./FixtureRow";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

interface CurrentRound {
  stage: string;
  stage_name: string;
  round_number: number | null;
}

export function MatchdayView({ leagueId }: { leagueId: number | null }) {
  const [round, setRound] = useState<number | null>(null);
  const [stageName, setStageName] = useState<string | null>(null);
  const [matches, setMatches] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(false);

  // Resolve which round is "current" for this league before fetching any
  // fixtures, instead of always starting from round 1.
  useEffect(() => {
    if (leagueId === null) return;
    setLoading(true);
    setRound(null);
    fetch(`${API_URL}/matches/${leagueId}/current`)
      .then((res) => res.json())
      .then((current: CurrentRound | null) => {
        setStageName(current?.stage_name ?? null);
        setRound(current?.round_number ?? 1);
      })
      .catch(() => setRound(1));
  }, [leagueId]);

  useEffect(() => {
    if (leagueId === null || round === null) return;
    fetch(`${API_URL}/matches/${leagueId}/round/${round}`)
      .then((res) => res.json())
      .then(setMatches)
      .catch(() => setMatches([]))
      .finally(() => setLoading(false));
  }, [leagueId, round]);

  if (leagueId === null) {
    return <div className="p-8 text-center text-sm text-muted-foreground">Select a league to see matchdays.</div>;
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <button
          onClick={() => setRound((r) => Math.max(1, (r ?? 1) - 1))}
          className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:border-border-strong hover:bg-muted"
        >
          ← Previous
        </button>
        <span className="text-sm font-medium text-primary">
          {stageName ?? "Round"} {round ?? ""}
        </span>
        <button
          onClick={() => setRound((r) => (r ?? 1) + 1)}
          className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:border-border-strong hover:bg-muted"
        >
          Next →
        </button>
      </div>

      {loading ? (
        <FixtureListSkeleton />
      ) : (
        <div key={`${leagueId}-${round}`} className="fixture-list-enter overflow-hidden rounded-lg border border-border bg-card">
          {matches.length === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">No matches found.</div>
          )}
          {matches.map((m) => (
            <FixtureRow key={m.id} fixture={m} />
          ))}
        </div>
      )}
    </div>
  );
}
