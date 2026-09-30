"use client";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Fixture } from "@/lib/types";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { useLiveMergedFixtures } from "@/hooks/useLiveUpdates";
import { useUrlParamSetter } from "@/hooks/useUrlParam";
import { Panel, EmptyState, ErrorState } from "@/components/common/Panel";
import { PaginatedHeader } from "@/components/common/PaginatedHeader";
import { FixtureRow, FixtureListSkeleton } from "./FixtureRow";

interface CurrentRound {
  stage: string;
  stage_name: string;
  round_number: number | null;
}

export function MatchdayView({ leagueId }: { leagueId: number | null }) {
  const isSelectable = leagueId !== null && leagueId !== WORLD_FOOTBALL_ID;
  const searchParams = useSearchParams();
  const setUrlParam = useUrlParamSetter();

  const { data: current, loading: currentLoading } = useJsonFetch<CurrentRound>(isSelectable ? `/matches/${leagueId}/current` : null);
  const [round, setRound] = useState<number | null>(() => {
    const r = Number(searchParams.get("round"));
    return Number.isInteger(r) && r > 0 ? r : null;
  });
  // `current` only ever changes on mount or on a real league switch (its
  // fetch isn't polled) — so this only needs to skip the very first
  // resolution when a URL-seeded round is already in `round`. Any later
  // firing is a genuine league change, where the old round no longer
  // applies and should be overwritten same as before.
  const skipNextResolve = useRef(round !== null);

  // Resolve which round is "current" for this league before fetching any
  // fixtures, instead of always starting from round 1 — but let Prev/Next
  // (or a URL-seeded round from a reload/shared link) override it locally
  // afterward without re-resolving on every click. The loading-gate is
  // checked before the skip flag on purpose: while the /current fetch is
  // still pending, this effect fires but must leave the skip flag armed —
  // otherwise it gets consumed on that pending pass, and the *next* firing
  // (once the fetch settles) sails straight through and overwrites the
  // URL-seeded round with the freshly-resolved "current" one anyway.
  useEffect(() => {
    if (isSelectable && currentLoading) return;
    if (skipNextResolve.current) {
      skipNextResolve.current = false;
      return;
    }
    setRound(current?.round_number ?? (isSelectable ? 1 : null));
  }, [current, currentLoading, isSelectable]);

  // Computed from `round` directly (already in scope, and this only ever
  // runs from a click handler) rather than via setRound's functional-updater
  // form — React can invoke that updater during render, and setUrlParam's
  // router.replace is a side effect that isn't allowed to live inside it.
  function updateRound(updater: (r: number | null) => number | null) {
    const next = updater(round);
    setRound(next);
    setUrlParam("round", next !== null ? String(next) : null);
  }

  // Polled — a round can contain a live match, and its current_minute only
  // updates in the DB, this re-fetch is what carries that onto the screen.
  const { data: matches, loading, error } = useJsonFetch<Fixture[]>(
    isSelectable && round !== null ? `/matches/${leagueId}/round/${round}` : null,
    20000
  );
  // Live-patched on top of the polled REST list — instant on a status/score
  // change instead of waiting up to 20s for the next poll to pick it up.
  const liveMatches = useLiveMergedFixtures(matches);

  // Tracks whichever round is actually on screen, not whatever's just been
  // clicked — `round` itself updates synchronously on click, before the new
  // fetch resolves, and using it directly as the Panel's key below would
  // remount (and re-animate) the panel on the same render that's still
  // showing the *previous* round's stale data, before the real swap happens.
  const [displayKey, setDisplayKey] = useState(`${leagueId}-${round}`);
  useEffect(() => {
    if (matches) setDisplayKey(`${leagueId}-${round}`); // eslint-disable-line react-hooks/set-state-in-effect
    // Deliberately excludes leagueId/round — should read whatever the
    // CURRENT league/round is at the moment matches resolves, not re-fire
    // when either changes (that's the click, which this is meant to lag
    // behind).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matches]);

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
  //
  // Blank while `current` is still loading rather than falling back to a
  // generic "Round" — that fallback exists for cups (a real value, just not
  // loaded yet), but shown during the initial fetch it wrongly reads as the
  // final answer for a plain league too, flashing "Round 5" right before it
  // corrects itself to "Matchday 5".
  const roundLabel = currentLoading
    ? ""
    : current?.stage === "regular-season"
      ? `Matchday ${round ?? ""}`
      : `${current?.stage_name ?? "Round"} ${round ?? ""}`;

  return (
    <div>
      <PaginatedHeader
        label={roundLabel}
        onPrev={() => updateRound((r) => Math.max(1, (r ?? 1) - 1))}
        onNext={() => updateRound((r) => (r ?? 1) + 1)}
      />

      {loading || round === null ? (
        <FixtureListSkeleton />
      ) : (
        <Panel className="fixture-list-enter" key={displayKey}>
          {(!liveMatches || liveMatches.length === 0) &&
            (error ? <ErrorState>Couldn&apos;t load matches — try again shortly.</ErrorState> : <EmptyState>No matches found.</EmptyState>)}
          {liveMatches?.map((m) => <FixtureRow key={m.id} fixture={m} showDate />)}
        </Panel>
      )}
    </div>
  );
}
