"use client";
import { useEffect, useState } from "react";
import { Fixture } from "@/lib/types";

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
    return <div>Select a league to see matchdays.</div>;
  }

  return (
    <div>
      <div>
        <button onClick={() => setRound((r) => Math.max(1, (r ?? 1) - 1))}>Previous</button>
        <span> {stageName ?? "Round"} {round ?? ""} </span>
        <button onClick={() => setRound((r) => (r ?? 1) + 1)}>Next</button>
      </div>
      {loading && <div>Loading...</div>}
      <ul>
        {!loading && matches.length === 0 && <li>No matches found.</li>}
        {matches.map((m) => (
          <li key={m.id}>
            {m.home_team} {m.home_score ?? "-"} : {m.away_score ?? "-"} {m.away_team} ({m.status})
          </li>
        ))}
      </ul>
    </div>
  );
}
