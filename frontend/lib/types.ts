export interface Match {
  id: number;
  league_id: number;
  home_team: string;
  home_team_id: number;
  away_team_id: number;
  away_team: string;
  home_coach_id: number | null;
  away_coach_id: number | null;
  referee_id: number | null;
  round_number: number | null;
  round_name: string | null;
  group_name: string | null;
  stage: string | null;
  stage_name: string | null;
  home_score: number | null;
  away_score: number | null;
  current_minute: number | null;
  status: string;
  event_date: string;
  last_updated: string;
}