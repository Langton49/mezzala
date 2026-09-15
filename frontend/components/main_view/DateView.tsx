"use client";
import { useEffect, useState } from "react";
import { Fixture } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function toDateParam(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function DateView() {
  const [date, setDate] = useState(() => new Date());
  const [matches, setMatches] = useState<Fixture[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/matches/date/${toDateParam(date)}`)
      .then((res) => res.json())
      .then(setMatches)
      .catch(() => setMatches([]));
  }, [date]);

  function shiftDay(delta: number) {
    setDate((d) => {
      const next = new Date(d);
      next.setDate(next.getDate() + delta);
      return next;
    });
  }

  return (
    <div>
      <div>
        <button onClick={() => shiftDay(-1)}>Previous day</button>
        <span> {toDateParam(date)} </span>
        <button onClick={() => shiftDay(1)}>Next day</button>
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
