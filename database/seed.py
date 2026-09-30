import httpx
from config.settings import settings
from config.leagues import LEAGUES
import asyncio
from database.repository import upsert_batch, transform_fixture, current_season_start
from database.database import async_session

client = httpx.AsyncClient(
    base_url=settings.bzzorio_base_url,
    headers={"Authorization": f"Token {settings.bzzorio_api_key}"},
    timeout=10.0  
)

async def seed(league_id: int):
    """Seed database with all fixtures for the current season. Planned as initial step during deployment

    Args:
        league_id (int): Competition id
    """
    try:
        upcoming_fixtures = []
        fixtures = await client.get(f"events/", params={"league_id": league_id, "status": "upcoming", "date_from": current_season_start().strftime("%Y-%m-%d"), "limit": 10})
        fixtures.raise_for_status() 
 
        while fixtures.status_code == 200:
            upcoming_fixtures.extend([transform_fixture(fx) for fx in fixtures.json()['results']])
            fixtures = await client.get(f"{fixtures.json()['next']}")
            
        async with async_session() as db:
            await upsert_batch(db, upcoming_fixtures)
            
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        
async def main():
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(seed(details.get("bzzorio_id"))) for details in LEAGUES.values()]
        
if __name__ == "__main__":
    asyncio.run(main())