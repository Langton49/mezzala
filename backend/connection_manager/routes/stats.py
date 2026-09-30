from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from backend.types.types import StatOut
from database.repository import get_current_stage, get_stat

stat_router = APIRouter()

@stat_router.get("/stats/{league_id}/{stat}", response_model=list[StatOut])
async def get_league_stats(league_id: int, stat: str, db: AsyncSession = Depends(get_session)):
    curr_season = await get_current_stage(db, league_id)
    if curr_season is None:
        return []
    return await get_stat(db, league_id, curr_season.season_id, stat)