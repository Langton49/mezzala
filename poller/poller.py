import httpx
import redis
import json
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture
from database.repository import upsert_fixture, orm_to_dict
from database.database import async_session
from datetime import datetime, timezone
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

def matches_changed(match_id: int, fixture_data: dict) -> bool:
    last_snapshot = (
        fixture_data["status"],
        fixture_data["home_score"],
        fixture_data["away_score"],
        fixture_data["current_minute"],
    )
    
    if LIVE_MATCHES_STORE.get(match_id) == last_snapshot:
        return False
    LIVE_MATCHES_STORE[match_id] = last_snapshot
    return True

def transform_fixture(dictionary: dict) -> dict:
    return {
        "match_id": dictionary["id"],
        "league_id": dictionary["league_id"],
        "home_team_id": dictionary["home_team_id"],
        "home_team": dictionary["home_team"],
        "away_team_id": dictionary["away_team_id"],
        "away_team": dictionary["away_team"],
        "venue_id": dictionary.get("venue_id"),
        "event_date": datetime.fromisoformat(dictionary["event_date"]),
        "status": dictionary["status"],
        "home_score": dictionary.get("home_score"),
        "away_score": dictionary.get("away_score"),
        "current_minute": dictionary.get("current_minute"),
        "home_score_ht": dictionary.get("home_score_ht"),
        "away_score_ht": dictionary.get("away_score_ht"),
        "last_updated": datetime.fromisoformat(dictionary["last_updated"])
    }

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
        # ----- TEST -------
        if not live_response:
            return [Fixture(**transform_fixture(test_fixture_data))]
        return [Fixture(**transform_fixture(fx)) for fx in live_response]
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")

async def fetch_league_fixtures(league_id: int) -> list[Fixture]:
    """Fetch upcoming league fixtures by league id

    Args:
        league_id (int): The league id associated with the desired league tied to id field in LEAGUES

    Returns:
        list[Fixture]: A list of the Fixture object for each response fixture from the API
    """
    try:
        fixture_request = client.get(f"events/", params={"league_id": league_id, "status": "upcoming", "date_from": f"{datetime.now().strftime("%Y-%m-%d")}", "limit": 10})
        fixture_request.raise_for_status()
        league_fixtures = fixture_request.json()["results"]
        return [Fixture(**transform_fixture(fx)) for fx in league_fixtures]
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        
async def fetch_fixture(match_id: int) -> Fixture:
    """Fetch individual fixture by its id

    Args:
        match_id (int): Fixture id from API

    Returns:
        Fixture: Fixture object for postgres table
    """
    try:
        fixture_request = client.get(f"events/", params={"match_id": match_id})
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
                print(f"{fx.home_team} {fx.home_score} - {fx.away_score} {fx.away_team}")
                print(f"Time: {fx.current_minute}")
                print("=" * 80)
                await upsert_fixture(db, orm_to_dict(fx))
                # if matches_changed(fx.match_id, orm_to_dict(fx)):
                redis_client.publish(
                    "match-updates",
                    json.dumps(orm_to_dict(fx), default=str)
                )
                
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_live_fixtures, "interval", seconds=5, id="live_fixtures")
    scheduler.start()
    
    print(f"Poller running")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        
if __name__ == "__main__":
    asyncio.run(main())