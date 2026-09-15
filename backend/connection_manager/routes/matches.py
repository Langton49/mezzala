from fastapi import FastAPI, WebSocket, APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from backend.app.connection_manager import manager
from uuid import uuid4
from database.database import get_session
from database.repository import get_matches_by_round, get_matches_by_id_date, get_matches_by_date
from backend.types.types import FixtureOut
from datetime import datetime

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

@matches_routes.get("/matches/{league_id}/round/{round}", response_model=list[FixtureOut])
async def get_round_matches(league_id: str, round: int, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_round(db, int(league_id), round)

@matches_routes.get("/matches/{league_id}/date/{date}", response_model=list[FixtureOut])
async def get_id_date_matches(league_id: str, date: str, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_id_date(db, int(league_id), datetime.fromisoformat(date))
        
@matches_routes.get("/matches/date/{date}", response_model=list[FixtureOut])
async def get_date_matches(date: str, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_date(db, datetime.fromisoformat(date))