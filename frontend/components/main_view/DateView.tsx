"use client";
import { useState } from "react";
import { Fixture } from "@/lib/types";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { Panel, EmptyState } from "@/components/common/Panel";
import { PaginatedHeader } from "@/components/common/PaginatedHeader";
import { FixtureRow, FixtureListSkeleton } from "./FixtureRow";

function toDateParam(date: Date): string {
  return date.toISOString().slice(0, 10);
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
  const { data: matches, loading } = useJsonFetch<Fixture[]>(path);

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
