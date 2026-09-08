import redis.asyncio as redis
import json
from config import settings
from backend.app.connection_manager import manager


async def redis_listener():
    client = redis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe("match-updates")
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        await manager.broadcast(json.loads(message["data"]))
    