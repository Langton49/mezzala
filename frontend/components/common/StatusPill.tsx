interface StatusPillProps {
  status: string;
  eventDate?: string;
  currentMinute?: number | null;
}

function formatKickoff(eventDate?: string): string {
  if (!eventDate) return "";
  const d = new Date(eventDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function StatusPill({ status, eventDate, currentMinute }: StatusPillProps) {
  if (status === "live") {
    return (
      <span className="flex items-center gap-1.5 text-xs font-semibold text-live">
        <span className="live-dot h-1.5 w-1.5 rounded-full bg-live" />
        {currentMinute != null ? `${currentMinute}'` : "LIVE"}
      </span>
    );
  }

  if (status === "finished") {
    return <span className="text-xs font-medium text-finished-foreground">FT</span>;
  }

  if (status === "postponed") {
    return <span className="text-xs font-medium text-live">PP</span>;
  }

  return <span className="text-xs text-muted-foreground tabular-nums">{formatKickoff(eventDate)}</span>;
}
