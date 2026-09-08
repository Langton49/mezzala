from fastapi import FastAPI, WebSocket 
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.websocket("/ws/live")
async def live_scores(ws: WebSocket, leagues: str = ""):
    pass