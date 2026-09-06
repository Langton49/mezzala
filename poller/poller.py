import httpx
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture, LiveFixture
from database.repository import upsert_fixture, upsert_live_fixture, orm_to_dict
from database.database import async_session
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

"""
Poller is the singleton service that fetches match info and news from external APIs. In terms of writing to DB and Redis no other service should do that
The poller should do the following tasks:
X) Fetch data from APIs and RSS feeds
X) Normalize to match the expected data structure with proper labels
3.) Compare against what exists so we know what's changed since last update
4.) Upsert to postgres db
5.) Publish to Redis for websocket updates
6.) Do this every 15s for live data
"""
client = httpx.AsyncClient(
    base_url=settings.bzzorio_base_url,
    headers={"Authorization": f"Token {settings.bzzorio_api_key}"},
    timeout=10.0    
)

def transform_fixture(dictionary: dict) -> dict:
    return {
        "match_id": dictionary["id"],
        "league_id": dictionary["league_id"],
        "home_team_id": dictionary["home_team_id"],
        "away_team_id": dictionary["away_team_id"],
        "home_team": dictionary["home_team"],
        "away_team": dictionary["away_team"],
        "venue_id": dictionary["venue_id"],
        "home_score": dictionary["home_score"],
        "away_score": dictionary["away_score"],
        "event_date": dictionary["event_date"]
    }
    
def transform_live_fixture(dictionary: dict) -> dict:
    return {
        "match_id": dictionary["id"],
        "league_id": dictionary["league_id"],
        "home_team_id": dictionary["home_team_id"],
        "away_team_id": dictionary["away_team_id"],
        "home_team": dictionary["home_team"],
        "away_team": dictionary["away_team"],
        "home_score": dictionary["home_score"],
        "away_score": dictionary["away_score"],
        "event_date": dictionary["event_date"],
        "current_minute": dictionary["current_minute"],
        "home_score_ht": dictionary["home_score_ht"],
        "away_score_ht": dictionary["away_score_ht"],
        "last_updated": dictionary["last_updated"]
    }

async def fetch_live_fixtures(league_id: int) -> list[LiveFixture]:
    """Fetch live fixtures from individual leagues by league id

    Args:
        league_id (int): League id from API

    Returns:
        list[LiveFixture]: List of LiveFixture objects
    """
    if not league_id:
        return []
    try:
        live_requests = await client.get(f"events/live/", params={"league_id": league_id})
        live_requests.raise_for_status()
        live_response = live_requests.json()['events']
        return [LiveFixture(**transform_live_fixture(fx)) for fx in live_response]
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
    for _, details in LEAGUES.items():
        fixtures = await fetch_live_fixtures(details.get("bzzorio_id", None))
        if not fixtures:
            continue
        for fx in fixtures:
            print(f"{fx.home_team} {fx.home_score} - {fx.away_score} {fx.away_team}")
            print(f"Time: {fx.current_minute}")
            
        async with async_session() as db:
            for live_fx in fixtures:
                await upsert_live_fixture(db, orm_to_dict(live_fx))
                
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