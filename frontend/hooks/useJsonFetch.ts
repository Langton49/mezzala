"use client";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Every fetch-driven view in this app (matchday, by-date, standings, stat
// cards) hand-rolled the same useEffect + fetch + loading/error state five
// times over. This is that pattern once. The dependency is just the path
// itself — callers build it from whatever props/state should trigger a
// re-fetch (leagueId, round, date, ...), so the URL changing IS the
// dependency, nothing extra to list separately or get out of sync.
export function useJsonFetch<T>(path: string | null): { data: T | null; loading: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(path !== null);

  useEffect(() => {
    if (path === null) {
      setData(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${API_URL}${path}`)
      .then((res) => res.json())
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    // Guards against a slow earlier request resolving after a faster later
    // one (e.g. clicking "Next" twice quickly) and clobbering fresher data.
    return () => {
      cancelled = true;
    };
  }, [path]);

  return { data, loading };
}
