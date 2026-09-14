from fastapi import FastAPI, WebSocket, APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from backend.app.connection_manager import manager
from uuid import uuid4
from database.database import get_session
from database.repository import get_matches_by_league
from backend.types.types import FixtureOut

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

@matches_routes.get("/matches/{league_id}/{stage}/{round}", response_model=list[FixtureOut])
async def get_upcoming_matches(league_id: str, stage: str, round: int, db: AsyncSession = Depends(get_session)):
    return await get_matches_by_league(db, int(league_id), stage, round)
        
