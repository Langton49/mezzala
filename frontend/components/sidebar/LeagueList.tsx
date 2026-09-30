"use client";

import { useDashboard, WORLD_FOOTBALL_ID } from "@/context/DashboardContext";
import { Logo } from "@/components/common/Logo";

const PLACEHOLDER_LEAGUES = [
    {id: 1, name: "Premier League"},
    {id: 3, name: "La Liga"},
    {id: 5, name: "BundesLiga"},
    {id: 6, name: " Ligue 1"},
    {id: 4, name: "Serie A"},
    {id: 7, name: "UEFA Champions League"},
    {id: 8, name: "UEFA Europa League"},
    {id: 83, name: "UEFA Conference League"},
    {id: 12, name: "Championship"},
    {id: 39, name: "FA Cup"},
    {id: 41, name: "Copa del Rey"},
    {id: 43, name: "DFB Pokal"},
    {id: 44, name: "Coupe de France"},
    {id: 42, name: "Coppa Italia"},
    {id:64, name: "UEFA Nations League"},
]

export function LeagueList(){
    const {currLeague, setCurrLeague} = useDashboard();

    function itemClass(active: boolean) {
        return `flex w-full items-center gap-2.5 rounded-md border-l-2 px-2.5 py-2 text-left text-sm transition-colors ${
            active
                ? "border-primary bg-muted font-medium text-primary"
                : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
        }`;
    }

    return (
        <ul className="flex flex-col gap-0.5 px-2">
            <li key="world-football">
                <button
                    onClick={() => setCurrLeague(WORLD_FOOTBALL_ID)}
                    title="World Football"
                    className={itemClass(currLeague === WORLD_FOOTBALL_ID)}
                >
                    <GlobeIcon size={18} />
                    <span className="truncate">World Football</span>
                </button>
            </li>
            <li key="sidebar-divider" className="my-1 border-t border-border" aria-hidden="true" />
            {
                PLACEHOLDER_LEAGUES.map((league) => {
                    const active = currLeague === league.id;
                    return (
                        <li key={league.id}>
                            <button
                                onClick={() => setCurrLeague(league.id)}
                                title={league.name}
                                className={itemClass(active)}
                            >
                                <Logo id={league.id} kind="league" alt={league.name} size={18} />
                                <span className="truncate">{league.name}</span>
                            </button>
                        </li>
                    );
                })
            }
        </ul>
    )
}

function GlobeIcon({ size }: { size: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0 text-current">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.2" />
            <ellipse cx="12" cy="12" rx="4" ry="9" stroke="currentColor" strokeWidth="1.2" />
            <path d="M3 12h18M4.5 7.5h15M4.5 16.5h15" stroke="currentColor" strokeWidth="1.2" />
        </svg>
    );
}
