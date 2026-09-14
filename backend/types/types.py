from pydantic import BaseModel, ConfigDict
from datetime import datetime

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