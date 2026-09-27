"use client";
import { useEffect, useState } from "react";
import { Standing } from "@/lib/types";
import { Logo } from "@/components/common/Logo";
import { Skeleton } from "@/components/common/Skeleton";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Only the "goal stats" are sortable, per the ask — position stays the
// natural sort order everywhere else, clicking a header just re-sorts by
// that stat instead of replacing the standings' own ordering permanently.
type SortKey = "gf" | "ga" | "gd";
type SortDir = "asc" | "desc";
interface Sort {
  key: SortKey;
  dir: SortDir;
}

export function StandingsView({ leagueId }: { leagueId: number | null }) {
  const [standings, setStandings] = useState<Standing[]>([]);
  const [loading, setLoading] = useState(false);
  const [sort, setSort] = useState<Sort | null>(null);

  useEffect(() => {
    if (leagueId === null) return;
    setLoading(true);
    setSort(null);
    fetch(`${API_URL}/standings/${leagueId}`)
      .then((res) => res.json())
      .then(setStandings)
      .catch(() => setStandings([]))
      .finally(() => setLoading(false));
  }, [leagueId]);

  if (leagueId === null) {
    return <div className="p-8 text-center text-sm text-muted-foreground">Select a league to see standings.</div>;
  }

  if (loading) {
    return <StandingsSkeleton />;
  }

  function toggleSort(key: SortKey) {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "desc" };
      if (prev.dir === "desc") return { key, dir: "asc" };
      return null; // third click: back to the table's natural position order
    });
  }

  const rows = sort
    ? [...standings].sort((a, b) => (sort.dir === "asc" ? a[sort.key] - b[sort.key] : b[sort.key] - a[sort.key]))
    : standings;

  const zoneColors = buildZoneColorMap(standings);

  return (
    <div>
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground">
              <th className="w-8 px-3 py-2 text-left font-medium">#</th>
              <th className="px-3 py-2 text-left font-medium">Team</th>
              <th className="w-8 px-2 py-2 text-center font-medium">W</th>
              <th className="w-8 px-2 py-2 text-center font-medium">D</th>
              <th className="w-8 px-2 py-2 text-center font-medium">L</th>
              <SortableHeader label="GF" sortKey="gf" sort={sort} onSort={toggleSort} />
              <SortableHeader label="GA" sortKey="ga" sort={sort} onSort={toggleSort} />
              <SortableHeader label="GD" sortKey="gd" sort={sort} onSort={toggleSort} />
              <th className="w-10 px-3 py-2 text-center font-semibold">Pts</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="p-8 text-center text-sm text-muted-foreground">
                  No standings available.
                </td>
              </tr>
            )}
            {rows.map((s) => (
              <StandingRow key={s.team_id} standing={s} zoneColors={zoneColors} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// zone_type only says the *family* a zone belongs to (qualification vs
// relegation) — a league can have more than one zone in the same family
// (Champions League and Europa League are both "qualification"), so those
// need visibly different colors from each other, not just from relegation.
// Assigned in order of first appearance in the table (i.e. by position),
// so the highest zone in a family always gets that family's boldest shade.
interface ZoneColor {
  border: string;
}
const QUALIFICATION_COLORS: ZoneColor[] = [
  { border: "border-l-blue-700" },
  { border: "border-l-sky-500" },
  { border: "border-l-cyan-400" },
  { border: "border-l-indigo-400" },
];
const RELEGATION_COLORS: ZoneColor[] = [
  { border: "border-l-red-600" },
  { border: "border-l-orange-500" },
];
const OTHER_ZONE_COLOR: ZoneColor = { border: "border-l-zinc-400" };

function buildZoneColorMap(standings: Standing[]): Map<string, ZoneColor> {
  const map = new Map<string, ZoneColor>();
  let qualificationCount = 0;
  let relegationCount = 0;
  for (const s of standings) {
    if (!s.zone_key || map.has(s.zone_key)) continue;
    if (s.zone_type === "qualification") {
      map.set(s.zone_key, QUALIFICATION_COLORS[qualificationCount % QUALIFICATION_COLORS.length]);
      qualificationCount++;
    } else if (s.zone_type === "relegation") {
      map.set(s.zone_key, RELEGATION_COLORS[relegationCount % RELEGATION_COLORS.length]);
      relegationCount++;
    } else {
      map.set(s.zone_key, OTHER_ZONE_COLOR);
    }
  }
  return map;
}

function StandingRow({ standing, zoneColors }: { standing: Standing; zoneColors: Map<string, ZoneColor> }) {
  const color = standing.zone_key ? zoneColors.get(standing.zone_key) : undefined;
  return (
    <tr
      className={`border-b border-l-4 border-border transition-colors last:border-b-0 hover:bg-muted ${color?.border ?? "border-l-transparent"}`}
      title={standing.zone_label ?? undefined}
    >
      <td className="px-3 py-2 tabular-nums text-muted-foreground">{standing.position}</td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <Logo id={standing.team_id} kind="team" alt={standing.team_name} size={18} />
          <span className="truncate">{standing.team_name}</span>
        </div>
      </td>
      <td className="px-2 py-2 text-center tabular-nums">{standing.won}</td>
      <td className="px-2 py-2 text-center tabular-nums">{standing.drawn}</td>
      <td className="px-2 py-2 text-center tabular-nums">{standing.lost}</td>
      <td className="px-2 py-2 text-center tabular-nums">{standing.gf}</td>
      <td className="px-2 py-2 text-center tabular-nums">{standing.ga}</td>
      <td className="px-2 py-2 text-center tabular-nums">{standing.gd}</td>
      <td className="px-3 py-2 text-center font-semibold tabular-nums">{standing.pts}</td>
    </tr>
  );
}

function SortableHeader({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  sort: Sort | null;
  onSort: (key: SortKey) => void;
}) {
  const active = sort?.key === sortKey;
  return (
    <th className="w-10 px-2 py-2 text-center font-medium">
      <button
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-0.5 transition-colors hover:text-foreground ${active ? "text-primary" : ""}`}
        aria-label={`Sort by ${label}`}
      >
        {label}
        {active && <span className="text-[10px] leading-none">{sort!.dir === "asc" ? "▲" : "▼"}</span>}
      </button>
    </th>
  );
}

function StandingsSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-border px-4 py-2.5 last:border-b-0">
          <Skeleton className="h-3 w-4" />
          <Skeleton className="h-5 w-5 rounded-full" />
          <Skeleton className="h-3 w-32" />
          <div className="ml-auto flex gap-4">
            {Array.from({ length: 6 }).map((__, j) => (
              <Skeleton key={j} className="h-3 w-5" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
