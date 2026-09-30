from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from backend.types.types import StandingsOut
from database.repository import get_current_stage, get_standings

standings_router = APIRouter()

@standings_router.get("/standings/{league_id}", response_model=list[StandingsOut])
async def get_league_standings(league_id: int, db: AsyncSession = Depends(get_session)):
    curr_season = await get_current_stage(db, league_id)
    if curr_season is None:
        return []
    return await get_standings(db, league_id, curr_season.season_id)