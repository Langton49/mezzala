export interface Fixture {
  id: number;
  league_id: number;
  home_team: string;
  away_team: string;
  home_team_id: number;
  away_team_id: number;
  home_coach_id: number | null;
  away_coach_id: number | null;
  referee_id: number | null;
  round_number: number | null;
  round_name: string | null;
  group_name: string | null;
  stage: string | null;
  stage_name: string | null;
  event_date: string;
  status: string;
  home_score: number | null;
  away_score: number | null;
}

export interface Standing {
  league_id: number;
  season_id: number;
  team_id: number;
  team_name: string;
  position: number;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
  xgf: number | null;
  xga: number | null;
  xgd: number | null;
  form: string | null;
  zone_key: string | null;
  zone_label: string | null;
  zone_type: string | null;
}

export interface PlayerStat {
  league_id: number;
  season_id: number;
  stat_type: string;
  rank: number;
  player_id: number;
  player_name: string;
  player_position: string | null;
  team_id: number;
  team_name: string;
  value: number;
  matches: number;
}

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