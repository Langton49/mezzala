"use client";
import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// How long a path-change fetch can be pending before we actually show the
// skeleton over already-rendered data. Below this it just reads as instant.
// Tuned against production, not localhost — the backend round-trip (Vercel
// frontend to Railway backend) typically runs 280-525ms, so anything near
// the old 150ms threshold meant nearly every navigation showed a skeleton
// for a perfectly normal request, not a genuinely slow one.
const SKELETON_DELAY_MS = 600;

// Every fetch-driven view in this app (matchday, by-date, standings, stat
// cards) hand-rolled the same useEffect + fetch + loading/error state five
// times over. This is that pattern once. The dependency is just the path
// itself — callers build it from whatever props/state should trigger a
// re-fetch (leagueId, round, date, ...), so the URL changing IS the
// dependency, nothing extra to list separately or get out of sync.
//
// `pollMs`, when given, re-fetches the same path on that interval in the
// background — without flipping `loading` back to true — so views that can
// show a live match (current_minute changes every few seconds server-side)
// stay current without the user having to navigate away and back. Callers
// that don't pass it keep the original fetch-once-per-path behavior.
export function useJsonFetch<T>(path: string | null, pollMs?: number): { data: T | null; loading: boolean; error: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [error, setError] = useState(false);
  // Kept out of the effect's dependency array on purpose — this only needs
  // to reflect whatever was on screen the instant a path change starts, not
  // retrigger the effect on every subsequent setData.
  const dataRef = useRef(data);

  useEffect(() => {
    dataRef.current = data;
  });

  useEffect(() => {
    if (path === null) {
      // Synchronizing local state with the `path` prop going null (not a
      // response arriving) — an intentional reset, not the "derive state
      // from a subscription callback" case this rule is meant to catch.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setData(null);
      setLoading(false);
      setError(false);
      return;
    }
    let cancelled = false;
    const hadData = dataRef.current !== null;

    function load(showLoading: boolean) {
      let loadingTimer: ReturnType<typeof setTimeout> | undefined;
      if (showLoading) {
        if (hadData) {
          // A round/date change when the previous list is still on screen —
          // only swap it for the skeleton if this fetch is actually slow.
          // Fast local responses resolve well under the delay, so the old
          // list just sits there until the new one replaces it, instead of
          // the skeleton flashing on and immediately back off.
          loadingTimer = setTimeout(() => {
            if (!cancelled) setLoading(true);
          }, SKELETON_DELAY_MS);
        } else {
          // Nothing rendered yet at all (first load) — show it immediately,
          // there's nothing else to keep displaying in the meantime.
          setLoading(true);
        }
      }
      fetch(`${API_URL}${path}`)
        .then((res) => {
          // A non-2xx response (e.g. the backend 500ing) still has a JSON
          // body in FastAPI's case — treating that as real data would hand
          // an error object to callers expecting an array and crash at
          // render time instead of surfacing a clean error state here.
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((json) => {
          if (!cancelled) {
            setData(json);
            setError(false);
          }
        })
        .catch(() => {
          // Deliberately not clearing `data` here — a transient failure on
          // a background poll shouldn't blank out a perfectly good list
          // that's already on screen, only flag that this refresh failed.
          if (!cancelled) setError(true);
        })
        .finally(() => {
          if (loadingTimer) clearTimeout(loadingTimer);
          if (!cancelled && showLoading) setLoading(false);
        });
    }

    load(true);
    const interval = pollMs ? setInterval(() => load(false), pollMs) : undefined;

    // Guards against a slow earlier request resolving after a faster later
    // one (e.g. clicking "Next" twice quickly) and clobbering fresher data.
    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [path, pollMs]);

  return { data, loading, error };
}
