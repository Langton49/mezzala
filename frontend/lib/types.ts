export interface Match {
  match_id: number;
  league_id: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  current_minute: number | null;
  status: string;
  event_date: string;
  last_updated: string;
}