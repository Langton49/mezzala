import asyncio
import websockets
import json

async def listen():
    async with websockets.connect("ws://localhost:8000/ws/live") as ws:
        async for message in ws:
            message = json.loads(message)
            print(f"{message["home_team"]} {message["home_score"]}-{message["away_score"]} {message["away_team"]}")

asyncio.run(listen())