"use client";
import { useEffect, useState } from "react";
import { Fixture } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export function MatchdayView({ leagueId }: { leagueId: number | null }) {
  const [round, setRound] = useState(1);
  const [matches, setMatches] = useState<Fixture[]>([]);

  useEffect(() => {
    if (leagueId === null) return;
    fetch(`${API_URL}/matches/${leagueId}/round/${round}`)
      .then((res) => res.json())
      .then(setMatches)
      .catch(() => setMatches([]));
  }, [leagueId, round]);

  if (leagueId === null) {
    return <div>Select a league to see matchdays.</div>;
  }

  return (
    <div>
      <div>
        <button onClick={() => setRound((r) => Math.max(1, r - 1))}>Previous</button>
        <span> Round {round} </span>
        <button onClick={() => setRound((r) => r + 1)}>Next</button>
      </div>
      <ul>
        {matches.length === 0 && <li>No matches found.</li>}
        {matches.map((m) => (
          <li key={m.id}>
            {m.home_team} {m.home_score ?? "-"} : {m.away_score ?? "-"} {m.away_team} ({m.status})
          </li>
        ))}
      </ul>
    </div>
  );
}
