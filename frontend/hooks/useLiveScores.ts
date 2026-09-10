"use client";
import { useEffect, useRef, useState } from "react";
import { Match } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/live";

export function useLiveScores() {
  const [matches, setMatches] = useState<Record<number, Match>>({});
  const retryDelay = useRef(1000);

  useEffect(() => {
    let ws: WebSocket;
    let cancelled = false;

    function connect() {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        retryDelay.current = 1000;
      };

      ws.onmessage = (event) => {
        const data: Match = JSON.parse(event.data);
        setMatches((prev) => ({ ...prev, [data.match_id]: data }));
      };

      ws.onclose = () => {
        if (cancelled) return;
        setTimeout(connect, retryDelay.current);
        retryDelay.current = Math.min(retryDelay.current * 2, 30000);
      };
    }

    connect();
    return () => {
      cancelled = true;
      ws?.close();
    };
  }, []);

  return Object.values(matches);
}