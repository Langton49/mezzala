"use client";
import { useEffect, useRef, useState } from "react";
import { Fixture } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000";

// What the poller actually publishes per change (database/repository.py's
// transform_fixture output, JSON-serialized as-is) — only the fields this
// app cares about applying live are named here. Deliberately not the full
// Fixture shape: the poller serializes event_date via Python's str(), not
// ISO 8601, so treating the payload as a full Fixture and blindly merging
// it would risk feeding a non-ISO date string into date-formatting code
// elsewhere. Only ever pull the four fields matches_changed() itself keys
// off of (poller.py) — everything else about a fixture doesn't change live.
export interface LiveFixtureUpdate {
  id: number;
  status: string;
  home_score: number | null;
  away_score: number | null;
  current_minute: number | null;
}

// Backend's poll_live_fixtures publishes a fixture's full snapshot to Redis
// the moment matches_changed() sees it differ from last time, and
// redis_listener.py relays that straight out over this socket to every
// connected client. REST polling (useJsonFetch's pollMs) still covers the
// case this misses — an initial fetch, and self-healing if the socket
// drops, since this reconnects on its own timer with no backoff/retry
// beyond "try again in a few seconds."
const RECONNECT_DELAY_MS = 3000;

export function useLiveUpdates(onUpdate: (fixture: LiveFixtureUpdate) => void) {
  const onUpdateRef = useRef(onUpdate);
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  });

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      ws = new WebSocket(`${WS_URL}/ws/live`);
      ws.onmessage = (event) => {
        try {
          const fixture = JSON.parse(event.data) as LiveFixtureUpdate;
          onUpdateRef.current(fixture);
        } catch {
          // Malformed payload — ignore this message, the socket itself is fine.
        }
      };
      ws.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);
}

// MatchdayView/DateView both need "start from the REST-fetched list, then
// patch individual fixtures in place as live updates arrive" — this is that
// pattern once. Re-syncs to `matches` whenever a new REST response (initial
// load or the 20s poll in useJsonFetch) comes in, and patches in between via
// the socket. A fixture not present in `matches` (wrong league/date for this
// view) is a no-op: the .map find just never matches its id.
export function useLiveMergedFixtures(matches: Fixture[] | null): Fixture[] | null {
  const [merged, setMerged] = useState<Fixture[] | null>(matches);

  useEffect(() => {
    // Synchronizing local state with the `matches` prop, not deriving state
    // from a subscription callback — the rule's concern doesn't apply here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMerged(matches);
  }, [matches]);

  useLiveUpdates((update) => {
    setMerged((prev) =>
      prev?.map((m) =>
        m.id === update.id
          ? { ...m, status: update.status, home_score: update.home_score, away_score: update.away_score, current_minute: update.current_minute }
          : m
      ) ?? prev
    );
  });

  return merged;
}
