interface StatusPillProps {
  status: string;
  currentMinute?: number | null;
}

// Shared so the kickoff-time-under-the-score display can format the same
// way as this used to when it lived here.
export function formatKickoff(eventDate?: string): string {
  if (!eventDate) return "";
  const d = new Date(eventDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

// Short calendar date ("Oct 10") — used where a single view can span more
// than one date (a matchday's fixtures aren't all on the same day), unlike
// formatKickoff, this is shown for finished matches too, not just upcoming.
export function formatShortDate(eventDate?: string): string {
  if (!eventDate) return "";
  const d = new Date(eventDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// The red pulsing dot + minute — a camera-style "recording" cue. Shared so
// the left-column status marker and the under-the-score live display (which
// replaces the date/time there entirely once a match goes live) render
// identically instead of two hand-copied versions drifting apart.
export function LiveIndicator({ currentMinute, className = "text-xs" }: { currentMinute?: number | null; className?: string }) {
  return (
    <span className={`flex items-center gap-1.5 font-semibold text-live ${className}`}>
      <span className="live-dot h-1.5 w-1.5 rounded-full bg-live" />
      {currentMinute != null ? `${currentMinute}'` : "LIVE"}
    </span>
  );
}

// Only renders an actual status marker (live/finished/postponed) now — a
// not-yet-started fixture has nothing to show here, its kickoff time moved
// to sit under the score instead.
export function StatusPill({ status, currentMinute }: StatusPillProps) {
  if (status === "live") {
    return <LiveIndicator currentMinute={currentMinute} />;
  }

  if (status === "finished") {
    return <span className="text-xs font-medium text-finished-foreground">FT</span>;
  }

  if (status === "postponed") {
    return <span className="text-xs font-medium text-live">PP</span>;
  }

  return null;
}
