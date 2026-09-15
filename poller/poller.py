import httpx
import redis
import json
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture
from database.repository import upsert_fixture, orm_to_dict, transform_fixture
from database.database import async_session
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
"""
Poller is the singleton service that fetches match info and news from external APIs. In terms of writing to DB and Redis no other service should do that
The poller should do the following tasks:
X) Fetch data from APIs and RSS feeds
X) Normalize to match the expected data structure with proper labels
3.) Compare against what exists so we know what's changed since last update. keeping the last seen in the pollers memory
X) Upsert to postgres db
5.) Publish to Redis for websocket updates
"""
test_fixture_data = {
    "id": 999999,
    "league_id": 1,
    "home_team_id": 42,
    "home_team": "Arsenal",
    "away_team_id": 49,
    "away_team": "Chelsea",
    "venue_id": None,
    "event_date": "2026-09-08T19:00:00+00:00",
    "status": "live",
    "home_score": 2,
    "away_score": 1,
    "current_minute": 58,
    "home_score_ht": 1,
    "away_score_ht": 1,
    "last_updated": "2026-09-08T19:00:00+00:00"
}

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

client = httpx.AsyncClient(
    base_url=settings.bzzorio_base_url,
    headers={"Authorization": f"Token {settings.bzzorio_api_key}"},
    timeout=10.0    
)
LIVE_MATCHES_STORE: dict[int, tuple] = {}

def matches_changed(fixture_id: int, fixture_data: dict) -> bool:
    last_snapshot = (
        fixture_data["status"],
        fixture_data["home_score"],
        fixture_data["away_score"],
        fixture_data["current_minute"],
    )

    if LIVE_MATCHES_STORE.get(fixture_id) == last_snapshot:
        return False
    LIVE_MATCHES_STORE[fixture_id] = last_snapshot
    return True

async def fetch_live_fixtures(league_id: int) -> list[Fixture]:
    """Fetch live fixtures from individual leagues by league id

    Args:
        league_id (int): League id from API

    Returns:
        list[Fixture]: List of Fixture objects
    """
    if not league_id:
        return []
    try:
        live_requests = await client.get(f"events/live/", params={"league_id": league_id})
        live_requests.raise_for_status()
        live_response = live_requests.json()['events']
        return [Fixture(**transform_fixture(fx)) for fx in live_response]
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")

async def fetch_fixtures_by_id(league_id: int, round: int, comp: str) -> list[Fixture]:
    """Fetch upcoming league fixtures by league id

    Args:
        league_id (int): The league id associated with the desired league tied to id field in LEAGUES

    Returns:
        list[Fixture]: A list of the Fixture object for each response fixture from the API
    """
    try:
        fixture_request = await client.get(f"events/", params={"league_id": league_id, "status": "upcoming", "stage": "regular-season", "round": round, "date_from": f"{datetime.now().strftime("%Y-%m-%d")}", "date_to": f"{datetime.now().strftime("%Y-%m-%d") + timedelta(days=7)}"})
        fixture_request.raise_for_status()
        league_fixtures = fixture_request.json()["results"]
        return [Fixture(**transform_fixture(fx)) for fx in league_fixtures]
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")

async def fetch_fixtures_by_date(date: datetime):
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=7)
    res = []
    try:
        fixture_request = await client.get(f"events/", params={"date_from": f"{day_start}", "date_to": f"{day_end}"})
        fixture_request.raise_for_status()
        while fixture_request.status_code == 200:
            res.extend([Fixture(**transform_fixture(fx)) for fx in fixture_request.json()["results"]])
            fixture_request = await client.get(f"{fixture_request.json()["next"]}")
        
        res = [fx for fx in res if fx.league_id in set([det.get("bzzorio_id", 0) for det in LEAGUES.values()])]
        return res
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        
async def fetch_fixture(fixture_id: int) -> Fixture:
    """Fetch individual fixture by its id

    Args:
        fixture_id (int): Fixture id from API

    Returns:
        Fixture: Fixture object for postgres table
    """
    try:
        fixture_request = client.get(f"events/{fixture_id}")
        fixture_request.raise_for_status()
        fixture  = fixture_request.json()
        return Fixture(**transform_fixture(fixture))
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    
async def fetch_standings(league_id: int) -> list[dict]:
    """Fetch the league table for a given leagues id

    Args:
        league_id (int): League id from the API

    Returns:
        list[dict]: List of each teams entry in the league table. Each dict contains team stats as well as position for the league table
    """
    try:
        standings_request = client.get(f"leagues/{league_id}/standings")
        standings_request.raise_for_status()
        standings = standings_request.json()['standings']
        return standings
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        
async def fetch_stat(league_id: int, stat: str) -> list[dict]:
    """Fetch specified stat `stat` from the API for the given league id

    Args:
        league_id (int): League id from API
        stat (str): Requested stat table ["scorers", "assists", "yellowcards", "redcards", "fouls"]

    Returns:
        list[dict]: List of each players entry in the stat table along with the stats and position. The main stat (i.e. Goal, Assist) is represented by the value key
    """
    try:
        stat_request = client.get(f"leagues/{league_id}/top/{stat}")
        stat_request.raise_for_status()
        stats = stat_request.json()['leaders']
        return stats
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")

async def poll_live_fixtures():
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_live_fixtures(details.get("bzzorio_id"))) for details in LEAGUES.values()]
        
    async with async_session() as db: 
        for response in requests:
            league_fixtures = response.result()
            if isinstance(league_fixtures, Exception) or not league_fixtures:
                continue
            
            for fx in league_fixtures:
                print(f"Upserting match with id: {fx.id}")
                await upsert_fixture(db, orm_to_dict(fx))
                if matches_changed(fx.id, orm_to_dict(fx)):
                    redis_client.publish(
                        "match-updates",
                        json.dumps(orm_to_dict(fx), default=str)
                    )

async def poll_upcoming_matches():
    """Fetch and upsert fixtures for the next week to ensure fixtures in postgres arent stale when venues, managers or referees change
    """
    current_day = datetime.now()
    fixtures = await fetch_fixtures_by_date(current_day)
    async with async_session() as db:
        print(f"Daily poll for upcoming matches")
        for fx in fixtures:
            await upsert_fixture(db, orm_to_dict(fx))
                
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_live_fixtures, "interval", seconds=5, id="live_fixtures")
    scheduler.add_job(poll_upcoming_matches, "interval", days=1, id="upcoming_matches", next_run_time=datetime.now())
    scheduler.start()
    
    print(f"Poller running")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        
if __name__ == "__main__":
    asyncio.run(main())