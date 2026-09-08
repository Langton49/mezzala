from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from backend.app.connection_manager import manager
from backend.app.redis_listener import redis_listener
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(redis_listener())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.websocket("/ws/live")
async def live_scores(ws: WebSocket):
    conn_id = str(uuid4())
    await manager.connect(conn_id, ws)
    try:
        while True:
            await ws.receive_text()
    except:
        manager.disconnect(conn_id)