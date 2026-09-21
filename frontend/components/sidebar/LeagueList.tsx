"use client";

import { useDashboard } from "@/context/DashboardContext";
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
    return (
        <ul className="flex flex-col gap-0.5 px-2">
            {
                PLACEHOLDER_LEAGUES.map((league) => {
                    const active = currLeague === league.id;
                    return (
                        <li key={league.id}>
                            <button
                                onClick={() => setCurrLeague(league.id)}
                                className={`flex w-full items-center gap-2.5 rounded-md border-l-2 px-2.5 py-2 text-left text-sm transition-colors ${
                                    active
                                        ? "border-primary bg-muted font-medium text-primary"
                                        : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                                }`}
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
