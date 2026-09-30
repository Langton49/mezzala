from pydantic import BaseModel, ConfigDict
from datetime import datetime

"""Types to match ORM types with Python types so proper JSON is sent to the frontend
"""

class FixtureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    league_id: int
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    home_coach_id: int | None
    away_coach_id: int | None
    referee_id: int | None
    round_number: int | None
    round_name: str | None
    group_name: str | None
    stage: str | None
    stage_name: str | None
    event_date: datetime
    status: str
    home_score: int | None
    away_score: int | None
    current_minute: int | None

class StandingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    league_id: int
    season_id: int
    team_id: int
    team_name: str
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    gd: int
    pts: int
    xgf: float | None
    xga: float | None
    xgd: float | None
    form: str | None
    zone_key: str | None
    zone_label: str | None
    zone_type: str | None
    
class StatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    league_id: int
    season_id: int
    stat_type: str
    rank: int
    player_id: int
    player_name: str
    player_position: str | None
    team_id: int
    team_name: str
    value: int
    matches: int