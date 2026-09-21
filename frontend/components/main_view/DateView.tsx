"use client";
import { useEffect, useState } from "react";
import { Fixture } from "@/lib/types";
import { FixtureRow, FixtureListSkeleton } from "./FixtureRow";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function toDateParam(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function formatDisplayDate(date: Date): string {
  return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

export function DateView() {
  const [date, setDate] = useState(() => new Date());
  const [matches, setMatches] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/matches/date/${toDateParam(date)}`)
      .then((res) => res.json())
      .then(setMatches)
      .catch(() => setMatches([]))
      .finally(() => setLoading(false));
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
      <div className="mb-3 flex items-center justify-between">
        <button
          onClick={() => shiftDay(-1)}
          className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:border-border-strong hover:bg-muted"
        >
          ← Previous
        </button>
        <span className="text-sm font-medium text-primary">{formatDisplayDate(date)}</span>
        <button
          onClick={() => shiftDay(1)}
          className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:border-border-strong hover:bg-muted"
        >
          Next →
        </button>
      </div>

      {loading ? (
        <FixtureListSkeleton />
      ) : (
        <div key={toDateParam(date)} className="fixture-list-enter overflow-hidden rounded-lg border border-border bg-card">
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
