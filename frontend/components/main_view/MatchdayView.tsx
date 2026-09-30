"use client";
import { useEffect, useState } from "react";
import { Fixture } from "@/lib/types";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { Panel, EmptyState } from "@/components/common/Panel";
import { PaginatedHeader } from "@/components/common/PaginatedHeader";
import { FixtureRow, FixtureListSkeleton } from "./FixtureRow";

interface CurrentRound {
  stage: string;
  stage_name: string;
  round_number: number | null;
}

export function MatchdayView({ leagueId }: { leagueId: number | null }) {
  const isSelectable = leagueId !== null && leagueId !== WORLD_FOOTBALL_ID;

  const { data: current } = useJsonFetch<CurrentRound>(isSelectable ? `/matches/${leagueId}/current` : null);
  const [round, setRound] = useState<number | null>(null);

  // Resolve which round is "current" for this league before fetching any
  // fixtures, instead of always starting from round 1 — but let Prev/Next
  // override it locally afterward without re-resolving on every click.
  useEffect(() => {
    setRound(current?.round_number ?? (isSelectable ? 1 : null));
  }, [current, isSelectable]);

  // Polled — a round can contain a live match, and its current_minute only
  // updates in the DB, this re-fetch is what carries that onto the screen.
  const { data: matches, loading } = useJsonFetch<Fixture[]>(
    isSelectable && round !== null ? `/matches/${leagueId}/round/${round}` : null,
    20000
  );

  if (leagueId === null) {
    return <EmptyState>Select a league to see matchdays.</EmptyState>;
  }
  if (leagueId === WORLD_FOOTBALL_ID) {
    return <EmptyState>World Football doesn&apos;t have matchdays — pick a specific league.</EmptyState>;
  }

  // Domestic leagues only have one stage, "regular-season", and its bzzorio
  // stage_name ("Regular season") isn't how football fans actually refer to
  // a single round — "Matchday 5" is. Cup competitions have real, distinct
  // stage names (Quarterfinals, League phase, Playoff round, ...) that
  // already read correctly, so only the league case gets rewritten.
  const roundLabel =
    current?.stage === "regular-season" ? `Matchday ${round ?? ""}` : `${current?.stage_name ?? "Round"} ${round ?? ""}`;

  return (
    <div>
      <PaginatedHeader
        label={roundLabel}
        onPrev={() => setRound((r) => Math.max(1, (r ?? 1) - 1))}
        onNext={() => setRound((r) => (r ?? 1) + 1)}
      />

      {loading || round === null ? (
        <FixtureListSkeleton />
      ) : (
        <Panel className="fixture-list-enter" key={`${leagueId}-${round}`}>
          {(!matches || matches.length === 0) && <EmptyState>No matches found.</EmptyState>}
          {matches?.map((m) => <FixtureRow key={m.id} fixture={m} showDate />)}
        </Panel>
      )}
    </div>
  );
}
