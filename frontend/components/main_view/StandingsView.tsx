"use client";
import { useState } from "react";
import { Standing } from "@/lib/types";
import { WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { useJsonFetch } from "@/hooks/useJsonFetch";
import { Logo } from "@/components/common/Logo";
import { Skeleton } from "@/components/common/Skeleton";
import { EmptyState } from "@/components/common/Panel";

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
  const isSelectable = leagueId !== null && leagueId !== WORLD_FOOTBALL_ID;
  const { data: standingsData, loading } = useJsonFetch<Standing[]>(isSelectable ? `/standings/${leagueId}` : null);
  const [sort, setSort] = useState<Sort | null>(null);
  const standings = standingsData ?? [];

  if (leagueId === null) {
    return <EmptyState>Select a league to see standings.</EmptyState>;
  }
  if (leagueId === WORLD_FOOTBALL_ID) {
    return <EmptyState>World Football doesn&apos;t have standings — pick a specific league.</EmptyState>;
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
      <div className="overflow-hidden rounded-md border border-border bg-card">
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
                <td colSpan={9}>
                  <EmptyState>No standings available.</EmptyState>
                </td>
              </tr>
            )}
            {rows.map((s) => (
              <StandingRow key={s.team_id} standing={s} zoneColors={zoneColors} />
            ))}
          </tbody>
        </table>
      </div>
      <ZoneLegend standings={standings} zoneColors={zoneColors} />
    </div>
  );
}

// zone_key isn't reliable — bzzorio reuses the same key ("playoff") for
// genuinely different zones that only differ by label — so everything here
// keys off zone_label, the one field that actually distinguishes zones.
//
// Colors are assigned in two passes, not by table-appearance order, because
// appearance order doesn't track severity/desirability:
//   1. Any zone whose label names a specific European competition (Champions
//      League / Europa League / Conference League) gets that competition's
//      real color, regardless of position — recognizable at a glance instead
//      of an arbitrary shade.
//   2. Everything else is grouped as "good outcome" (qualification/playoff/
//      promotion zones) or "bad outcome" (relegation zones) and shaded on a
//      gradient — but ordered by how good/bad the zone actually is, not by
//      which one happens to sit higher in the table. A relegation *playoff*
//      zone can appear above direct relegation (Bundesliga: playoff spot is
//      16th, direct relegation is 17th-18th) while being the less severe of
//      the two, so relegation zones are ordered by how deep into the table
//      they reach (furthest down = most severe = boldest), the opposite of
//      simple appearance order.
interface ZoneColor {
  bg: string;
}

const EUROPEAN_COMPETITION_COLORS: { match: string; color: ZoneColor }[] = [
  // "Conference League" must be checked before "Europa League" would ever
  // need to be (they don't overlap, but keeping the longer/more specific
  // names first is the safer habit if more zone labels show up later).
  { match: "Conference League", color: { bg: "bg-green-300" } },
  { match: "Europa League", color: { bg: "bg-orange-300" } },
  { match: "Champions League", color: { bg: "bg-blue-300" } },
];

const GOOD_OUTCOME_GRADIENT: ZoneColor[] = [
  { bg: "bg-blue-300" },
  { bg: "bg-sky-300" },
  { bg: "bg-cyan-200" },
  { bg: "bg-indigo-200" },
];
const RELEGATION_GRADIENT: ZoneColor[] = [
  { bg: "bg-red-300" },
  { bg: "bg-red-200" },
];
const OTHER_ZONE_COLOR: ZoneColor = { bg: "bg-zinc-200" };

const GOOD_OUTCOME_TYPES = new Set(["qualification", "playoff", "promotion"]);

interface ZoneInfo {
  label: string;
  type: string | null;
  minPosition: number;
  maxPosition: number;
}

function buildZoneColorMap(standings: Standing[]): Map<string, ZoneColor> {
  const zones = new Map<string, ZoneInfo>();
  for (const s of standings) {
    if (!s.zone_label) continue;
    const existing = zones.get(s.zone_label);
    if (existing) {
      existing.minPosition = Math.min(existing.minPosition, s.position);
      existing.maxPosition = Math.max(existing.maxPosition, s.position);
    } else {
      zones.set(s.zone_label, {
        label: s.zone_label,
        type: s.zone_type,
        minPosition: s.position,
        maxPosition: s.position,
      });
    }
  }

  const map = new Map<string, ZoneColor>();
  const unbranded: ZoneInfo[] = [];

  for (const zone of zones.values()) {
    const brand = EUROPEAN_COMPETITION_COLORS.find((c) => zone.label.includes(c.match));
    if (brand) {
      map.set(zone.label, brand.color);
    } else {
      unbranded.push(zone);
    }
  }

  unbranded
    .filter((z) => GOOD_OUTCOME_TYPES.has(z.type ?? ""))
    .sort((a, b) => a.minPosition - b.minPosition) // best (lowest) position first
    .forEach((zone, i) => map.set(zone.label, GOOD_OUTCOME_GRADIENT[i % GOOD_OUTCOME_GRADIENT.length]));

  unbranded
    .filter((z) => z.type === "relegation")
    .sort((a, b) => b.maxPosition - a.maxPosition) // deepest-reaching zone first = most severe
    .forEach((zone, i) => map.set(zone.label, RELEGATION_GRADIENT[i % RELEGATION_GRADIENT.length]));

  for (const zone of unbranded) {
    if (!map.has(zone.label)) map.set(zone.label, OTHER_ZONE_COLOR);
  }

  return map;
}

function StandingRow({ standing, zoneColors }: { standing: Standing; zoneColors: Map<string, ZoneColor> }) {
  const color = standing.zone_label ? zoneColors.get(standing.zone_label) : undefined;
  // A plain hover:bg-muted would blank out the zone tint on hover, and
  // brightness-95 does nothing on a row with no background at all — so
  // zoned and unzoned rows need different hover treatments, not one shared
  // class, to both actually show feedback.
  const hoverClass = color ? "hover:brightness-95" : "hover:bg-muted";
  return (
    <tr
      className={`border-b border-border transition-colors last:border-b-0 ${hoverClass} ${color?.bg ?? ""}`}
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

function ZoneLegend({ standings, zoneColors }: { standings: Standing[]; zoneColors: Map<string, ZoneColor> }) {
  const labels = new Set<string>();
  for (const s of standings) {
    if (s.zone_label) labels.add(s.zone_label);
  }
  if (labels.size === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {[...labels].map((label) => (
        <span key={label} className="flex items-center gap-1.5">
          <span className={`h-2.5 w-2.5 rounded-sm border border-border-strong ${zoneColors.get(label)?.bg ?? "bg-transparent"}`} />
          {label}
        </span>
      ))}
    </div>
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
    <div className="overflow-hidden rounded-md border border-border bg-card">
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
