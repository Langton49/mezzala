"use client";
import { useDashboard } from "@/context/DashboardContext";
import { Ribbon } from "./Ribbon";
import { StandingsView } from "./StandingsView";
import { PlayerStatsView } from "./PlayerStatsView";
import { FixturesView } from "./FixtureView";

export function MainView(){
    const {currTab, currLeague} = useDashboard();

    return(
        <div className="flex flex-col">
            <Ribbon/>
            <div className="flex-1 overflow-auto p-4">
                {currTab === "standings" && <StandingsView leagueId={currLeague}/>}
                {currTab === "fixtures" && <FixturesView leagueId={currLeague}/>}
                {currTab === "stats" && <PlayerStatsView leagueId={currLeague}/>}
            </div>
        </div>
    )
}