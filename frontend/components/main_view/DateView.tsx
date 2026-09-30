"use client";
import { useState } from "react";
import { Fixture } from "@/lib/types";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { Panel, EmptyState } from "@/components/common/Panel";
import { PaginatedHeader } from "@/components/common/PaginatedHeader";
import { FixtureRow, FixtureListSkeleton } from "./FixtureRow";

// Built from local date parts, not toISOString() — that converts to UTC
// first, which silently shifts the date back a day for any timezone ahead
// of UTC during the hours after local midnight but before UTC catches up
// (e.g. local 00:30 in UTC+2 is still 22:30 UTC the previous day), so
// "today" was being requested from the backend as yesterday.
function toDateParam(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDisplayDate(date: Date): string {
  return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

export function DateView({ leagueId }: { leagueId: number | null }) {
  const [date, setDate] = useState(() => new Date());
  const dateParam = toDateParam(date);

  const path =
    leagueId === null
      ? null
      : leagueId === WORLD_FOOTBALL_ID
        ? `/matches/date/${dateParam}`
        : `/matches/${leagueId}/date/${dateParam}`;
  // Polled so a live match's current_minute keeps advancing without the
  // user having to shift days and back to force a re-fetch.
  const { data: matches, loading } = useJsonFetch<Fixture[]>(path, 20000);

  if (leagueId === null) {
    return <EmptyState>Select a league, or World Football, to see fixtures.</EmptyState>;
  }

  function shiftDay(delta: number) {
    setDate((d) => {
      const next = new Date(d);
      next.setDate(next.getDate() + delta);
      return next;
    });
  }

  return (
    <div>
      <PaginatedHeader label={formatDisplayDate(date)} onPrev={() => shiftDay(-1)} onNext={() => shiftDay(1)} />

      {loading ? (
        <FixtureListSkeleton />
      ) : (
        <Panel className="fixture-list-enter" key={dateParam}>
          {(!matches || matches.length === 0) && <EmptyState>No matches found.</EmptyState>}
          {matches?.map((m) => <FixtureRow key={m.id} fixture={m} />)}
        </Panel>
      )}
    </div>
  );
}
