"use client";

import { useDashboard } from "@/context/DashboardContext";

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
    return (<ul>
        {
            PLACEHOLDER_LEAGUES.map((league) => (
                <li key={league.id}>
                    <button
           onClick={()=>setCurrLeague(league.id)} className={currLeague === league.id ? "font-bold" : ""}>
            {league.name}
            </button> 
                </li>
            ))
        }
    </ul>)
}