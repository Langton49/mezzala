from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.redis_listener import redis_listener
import asyncio
from contextlib import asynccontextmanager
from backend.connection_manager.routes.matches import matches_routes

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

app.include_router(matches_routes)