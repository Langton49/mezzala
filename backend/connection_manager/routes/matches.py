from fastapi import WebSocket, APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.connection_manager import manager
from uuid import uuid4
from database.database import get_session
from database.repository import get_matches_by_round, get_matches_by_id_date, get_matches_by_date, get_current_round
from backend.types.types import FixtureOut
from datetime import date as DateParam

matches_routes = APIRouter()

@matches_routes.websocket("/ws/live")
async def live_scores(ws: WebSocket, leagues: str = ""):
    conn_id = str(uuid4())
    await manager.connect(conn_id, ws)
    try:
        while True:
            await ws.receive_text()
    except:
        manager.disconnect(conn_id)

# league_id/round/date are typed directly (int/date) rather than parsed by
# hand inside the body — FastAPI validates them itself and returns a clean
# 422 on bad input instead of an unhandled ValueError turning into a 500.
@matches_routes.get("/matches/{league_id}/round/{round}", response_model=list[FixtureOut])
async def get_round_matches(league_id: int, round: int, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_round(db, league_id, round)

@matches_routes.get("/matches/{league_id}/date/{date}", response_model=list[FixtureOut])
async def get_id_date_matches(league_id: int, date: DateParam, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_id_date(db, league_id, date)

@matches_routes.get("/matches/date/{date}", response_model=list[FixtureOut])
async def get_date_matches(date: DateParam, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_date(db, date)

@matches_routes.get("/matches/{league_id}/current")
async def get_current_league_round(league_id: int, db: AsyncSession = Depends(get_session)):
    return await get_current_round(db, league_id)