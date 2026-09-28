import httpx
import redis
import json
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture
from database.repository import upsert_fixture, upsert_stat, orm_to_dict, transform_stat, transform_fixture, transform_standings, transform_stage, upsert_stage, get_current_stage, upsert_standings
from database.database import async_session
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

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
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")

async def fetch_current_stage(league_id: int) -> list[dict]:
    try:
        req = await client.get(f"/leagues/{league_id}/season/")
        req.raise_for_status()
        result = req.json()['season']
        season_id = result['id']
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

async def fetch_fixtures_by_id(league_id: int, round: int) -> list[Fixture]:
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
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")

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
    except (KeyError, TypeError) as e:
            print(f"Unexpected Error")
        
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
    except (KeyError, TypeError) as e:
        print(f"Unexpected Error")
    
async def fetch_standings(league_id: int) -> list[dict]:
    """Fetch the league table for a given leagues id

    Args:
        league_id (int): League id from the API

    Returns:
        list[dict]: List of each teams entry in the league table. Each dict contains team stats as well as position for the league table
    """
    try:
        async with async_session() as db:
            curr_stage = await get_current_stage(db, league_id)
        if not curr_stage:
            raise Exception("Season id not found")
        curr_season = curr_stage.season_id
        standings_request = await client.get(f"leagues/{league_id}/standings/?season_id={curr_season}")
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
    fixtures = await fetch_fixtures_by_date(current_day - timedelta(days=5))
    async with async_session() as db:
        print(f"Daily poll for upcoming matches")
        for fx in fixtures:
            try:
                await upsert_fixture(db, orm_to_dict(fx))
            except Exception:
                print(f"Unexpected Error")
                
async def poll_stages():
    print("Daily poll for stages")
    async with async_session() as db:
        for details in LEAGUES.values():
            try:
                stages = await fetch_current_stage(details['bzzorio_id'])
                for stage in stages:
                    await upsert_stage(db, stage)
            except Exception:
                print(f"Error trying to poll for league with id {details['bzzorio_id']}")
                
async def poll_standings():
    print("Daily poll for league standings")
    async with async_session() as db:
        for details in LEAGUES.values():
            try:
                standings = await fetch_standings(details['bzzorio_id'])
                await upsert_standings(db, standings)
            except Exception:
                print(f"Error trying to poll for league with id {details['bzzorio_id']}")
            
async def poll_stat():
    print("Daily poll for stats")
    async with async_session() as db:
        for details in LEAGUES.values():
            try:
                stats = await fetch_stat(details['bzzorio_id'])
                await upsert_stat(db, stats)
            except Exception:
                print(f"Unexpected Error")
    print('Stat poll done')

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_live_fixtures, "interval", seconds=5, id="live_fixtures")
    scheduler.add_job(poll_upcoming_matches, "interval", days=1, id="upcoming_matches", next_run_time=datetime.now())
    scheduler.add_job(poll_stages, "interval", days=1, id="stages", next_run_time=datetime.now())
    scheduler.add_job(poll_standings, "interval", days=1, id="standings", next_run_time=datetime.now())
    scheduler.add_job(poll_stat, "interval", days=1, id='stats', next_run_time=datetime.now())
    scheduler.start()
    
    print(f"Poller running")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    
if __name__ == "__main__":
    asyncio.run(main())