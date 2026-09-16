import httpx
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture
import asyncio
from database.repository import upsert_batch, orm_to_dict, transform_fixture, current_season_start
from database.database import async_session

client = httpx.AsyncClient(
    base_url=settings.bzzorio_base_url,
    headers={"Authorization": f"Token {settings.bzzorio_api_key}"},
    timeout=10.0  
)

async def seed(league_id: int) -> list[Fixture]:
    try:
        upcoming_fixtures = []
        fixtures = await client.get(f"events/", params={"league_id": league_id, "status": "upcoming", "date_from": current_season_start().strftime("%Y-%m-%d"), "limit": 10})
        fixtures.raise_for_status() 
 
        while fixtures.status_code == 200:
            upcoming_fixtures.extend([orm_to_dict(Fixture(**transform_fixture(fx))) for fx in fixtures.json()['results']])
            fixtures = await client.get(f"{fixtures.json()['next']}")
        async with async_session() as db:
            await upsert_batch(db, upcoming_fixtures)
            
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")

async def get_curr_stage():
    try:
        struct = await client.get(f"leagues/7/seasons/")
        struct.raise_for_status()
        print(struct.json()['seasons'][0])
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        
async def main():
    await get_curr_stage()
    # for dets in LEAGUES.values():
    #     await seed(dets.get("bzzorio_id", 0))
        
if __name__ == "__main__":
    asyncio.run(main())