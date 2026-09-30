"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Fixture } from "@/lib/types";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { useLiveMergedFixtures } from "@/hooks/useLiveUpdates";
import { useUrlParamSetter } from "@/hooks/useUrlParam";
import { Panel, EmptyState, ErrorState } from "@/components/common/Panel";
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

// Inverse of toDateParam — also built from explicit y/m/d components rather
// than handed straight to `new Date(...)`, which treats a bare "YYYY-MM-DD"
// string as UTC midnight and would shift the displayed day back by one for
// any timezone behind UTC.
function parseDateParam(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const [, y, m, d] = match;
  return new Date(Number(y), Number(m) - 1, Number(d));
}

export function DateView({ leagueId }: { leagueId: number | null }) {
  const searchParams = useSearchParams();
  const setUrlParam = useUrlParamSetter();
  const [date, setDateState] = useState(() => {
    const raw = searchParams.get("date");
    return (raw && parseDateParam(raw)) || new Date();
  });
  const dateParam = toDateParam(date);

  // Computed from `date` directly rather than via setDateState's
  // functional-updater form — React can invoke that updater during render,
  // and setUrlParam's router.replace is a side effect that isn't allowed to
  // live inside it.
  function setDate(updater: (d: Date) => Date) {
    const next = updater(date);
    setDateState(next);
    setUrlParam("date", toDateParam(next));
  }

  const path =
    leagueId === null
      ? null
      : leagueId === WORLD_FOOTBALL_ID
        ? `/matches/date/${dateParam}`
        : `/matches/${leagueId}/date/${dateParam}`;
  // Polled so a live match's current_minute keeps advancing without the
  // user having to shift days and back to force a re-fetch.
  const { data: matches, loading, error } = useJsonFetch<Fixture[]>(path, 20000);
  const liveMatches = useLiveMergedFixtures(matches);

  // Tracks whichever date is actually on screen, not whichever's just been
  // clicked to — `dateParam` changes synchronously on click, before the new
  // fetch resolves, and using it directly as the Panel's key below would
  // remount (and re-animate) the panel while it's still showing the
  // *previous* date's stale data, before the real swap happens.
  const [displayKey, setDisplayKey] = useState(dateParam);
  useEffect(() => {
    if (matches) setDisplayKey(dateParam);
  }, [matches]);

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
        <Panel className="fixture-list-enter" key={displayKey}>
          {(!liveMatches || liveMatches.length === 0) &&
            (error ? <ErrorState>Couldn&apos;t load matches — try again shortly.</ErrorState> : <EmptyState>No matches found.</EmptyState>)}
          {liveMatches?.map((m) => <FixtureRow key={m.id} fixture={m} />)}
        </Panel>
      )}
    </div>
  );
}
