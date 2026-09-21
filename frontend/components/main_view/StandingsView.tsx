export function StandingsView({leagueId}: {leagueId: number | null}){
    return (
        <div className="p-8 text-center text-sm text-muted-foreground">
            {leagueId === null ? "Select a league to see standings." : "Standings coming soon."}
        </div>
    )
}
