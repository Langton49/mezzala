"use client";

import { useDashboard } from "@/context/DashboardContext";

const PLACEHOLDER_LEAGUES = [
    {id: 1, name: "Premier League"}
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