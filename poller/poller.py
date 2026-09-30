import httpx
import redis
import json
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture
from database.repository import upsert_fixtures, upsert_stat, transform_stat, transform_fixture, transform_standings, transform_stage, upsert_stages, get_current_stage, upsert_standings
from database.database import async_session
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# CONFIGS
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

LIVE_MATCHES_STORE: dict[int, tuple] = {}

# HELPERS
client = httpx.AsyncClient(
    base_url=settings.bzzorio_base_url,
    headers={"Authorization": f"Token {settings.bzzorio_api_key}"},
    timeout=10.0    
)

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

# POLL LIVE FIXTURES
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
        return [transform_fixture(fx) for fx in live_response]
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")

async def poll_live_fixtures():
    """Poll live fixtures using the live events endpoint and upsert them to db and if anything changes in realtime, redis
    """
    print("Live Fixtures poll running...")
    # Fetch live fixtures async
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_live_fixtures(details.get("bzzorio_id"))) for details in LEAGUES.values()]
        
    async with async_session() as db: 
        for response in requests:
            league_fixtures = response.result()
            if not league_fixtures:
                continue
            
            await upsert_fixtures(db, league_fixtures)
            for fx in league_fixtures:
                if matches_changed(fx.id, fx):
                    redis_client.publish(
                        "match-updates",
                        json.dumps(fx, default=str)
                    )

# POLL CURRENT COMPETITION STAGES
async def fetch_current_stage(league_id: int) -> list[dict]:
    """Fetch the current stage of competition with league id. Necessary because for competitions like UCL, these change over time

    Args:
        league_id (int): Competition league id

    Returns:
        list[dict]: List of all competition stages up until the most recent one
    """
    if not league_id:
        return []
    try:
        req = await client.get(f"/leagues/{league_id}/season/")
        req.raise_for_status()
        result = req.json()['season']
        season_id = result['id'] # Current season id
        
        comp_stages = []
        if result['is_current']:
            stages = result['stages']
            for idx, stage in enumerate(stages):
                comp_stages.append(transform_stage(stage, league_id, season_id, idx + 1))
                
        return comp_stages
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")
            
async def poll_stages():
    """A daily poll to check the current stage for each competition in LEAGUES
    """
    print("Starting stages poll...")
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_current_stage(details.get("bzzorio_id"))) for details in LEAGUES.values()]
            
    curr_stages = []
    async with async_session() as db:
        for response in requests:
            stages = response.result()
            if not stages:
                continue
            curr_stages.extend(stages)
            
        await upsert_stages(db, curr_stages)
    print("Stages poll complete.")

# POLL UPCOMING FIXTURES FOR THE NEXT 7 DAYS
async def fetch_upcoming_fixtures(league_id: int):
    """Fetch upcoming fixtures by their league id for the next 7 days. This is for clarity as match details can change after matches have already been seeded

    Args:
        league_id (int): Competition id
        date (datetime): 

    Returns:
        _type_: _description_
    """
    if not league_id:
        return []
    date = datetime.now()
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=7)
    res = []
    try:
        fixture_request = await client.get(f"events/", params={"league_id": league_id, "date_from": f"{day_start}", "date_to": f"{day_end}"})
        fixture_request.raise_for_status()
        
        # API response has a next endpoint for the next batch of fixtures within the range
        while fixture_request.status_code == 200:
            res.extend([transform_fixture(fx) for fx in fixture_request.json()["results"]])
            fixture_request = await client.get(f"{fixture_request.json()["next"]}")
        
        return res
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")
            
async def poll_upcoming_matches():
    """Fetch and upsert fixtures for the next week to ensure fixtures in postgres arent stale when venues, managers or referees change
    """
    print("Starting upcoming matches poll...")
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_upcoming_fixtures(details.get("bzzorio_id"))) for details in LEAGUES.values()]
    
    upcoming_fixtures = []
    async with async_session() as db:
        for response in requests:
            fixtures = response.result()
            if not fixtures:
                continue
            upcoming_fixtures.extend(fixtures)
            
        await upsert_fixtures(db, upcoming_fixtures)
            
    print("Upcoming matches poll complete")
    
# POLL LEAGUE STANDINGS FOR ALL COMPS
async def fetch_standings(league_id: int) -> list[dict]:
    """Fetch the league table for a given league's id

    Args:
        league_id (int): Competition id

    Returns:
        list[dict]: List of each teams entry in the league table. Each dict contains team stats as well as position for the league table
    """
    try:
        async with async_session() as db:
            curr_stage = await get_current_stage(db, league_id)
        if not curr_stage:
            raise Exception("Season id not found")
        
        curr_season = curr_stage.season_id
        standings_request = await client.get(f"leagues/{league_id}/standings/", params={"season_id": curr_season})
        standings_request.raise_for_status()
        standings = standings_request.json()['standings']
        standings = transform_standings(standings, league_id, curr_season)
        return standings
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError) as e:
        # Some competitions (e.g. national-team competitions like the
        # Nations League) don't return a flat 'standings' list at all — this
        # keeps that failure contained to this one function, matching every
        # other fetch_* here, rather than relying on the caller to catch it.
        print(f"Unexpected standings response shape for league {league_id}: {e}")
        
async def poll_standings():
    print("Starting standings poll...")
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_standings(details.get("bzzorio_id"))) for details in LEAGUES.values()]
    
    league_standings = []
    async with async_session() as db:
        for response in requests:
            standings = response.result()
            if not standings:
                continue
            league_standings.extend(standings)
        
        await upsert_standings(db, league_standings)
    print("Standings poll complete")        

# POLL PLAYER STATS FOR ALL COMPS
async def fetch_stat(league_id: int) -> list[dict]:
    """Fetch specified stat `stat` from the API for the given league id

    Args:
        league_id (int): League id from API
        stat (str): Requested stat table ["scorers", "assists", "yellowcards", "redcards", "fouls"]

    Returns:
        list[dict]: List of each players entry in the stat table along with the stats and position. The main stat (i.e. Goal, Assist) is represented by the value key
    """
    tags = ['scorers', 'assists', 'yellowcards', 'redcards', 'fouls']
    league_stats = []
    try:
        async with async_session() as db:
            curr_stage = await get_current_stage(db, league_id)
        if not curr_stage:
            raise Exception("Season id not found")
        curr_season = curr_stage.season_id
        
        for stat in tags:
            stat_request = await client.get(f"leagues/{league_id}/top/{stat}/")
            stat_request.raise_for_status()
            stats = stat_request.json()['leaders']
            league_stats.extend(transform_stat(stats, league_id, curr_season, stat))
        return league_stats
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")
            
async def poll_stat():
    """Poll player stats across all competitions
    """
    print("Starting stats poll...")
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_stat(details.get("bzzorio_id"))) for details in LEAGUES.values()]
        
    player_stats = []
    async with async_session() as db:
        for response in requests:
            stats = response.result()
            if not stats:
                continue
            player_stats.extend(stats)
            
        await upsert_stat(db, player_stats)
    print('Stats poll complete')

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_live_fixtures, "interval", seconds=5, id="live_fixtures")
    scheduler.add_job(poll_upcoming_matches, "interval", days=1, id="upcoming_matches", next_run_time=datetime.now())
    scheduler.add_job(poll_stages, "interval", days=1, id="stages", next_run_time=datetime.now())
    scheduler.add_job(poll_standings, "interval", days=1, id="standings", next_run_time=datetime.now())
    scheduler.add_job(poll_stat, "interval", days=1, id='stats', next_run_time=datetime.now())
    scheduler.start()
    
    print("POLLER UP")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    
if __name__ == "__main__":
    asyncio.run(main())