import httpx
import redis.asyncio as redis
import json
from config.settings import settings
from config.leagues import LEAGUES
from database.repository import upsert_fixtures, upsert_stat, transform_stat, transform_fixture, transform_standings, transform_stage, upsert_stages, get_current_stage, upsert_standings, current_season_start, has_fixtures_for_season
from database.database import async_session
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# CONFIGS
# Async + settings.redis_url (not a hardcoded localhost sync client) — this
# has to match backend/app/redis_listener.py's connection or the poller
# publishes into a Redis instance nothing is actually subscribed to in any
# non-local deployment, and a sync client here would block the poller's
# event loop on every publish.
redis_client = redis.from_url(settings.redis_url)

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
async def fetch_live_fixtures(league_id: int) -> list[dict]:
    """Fetch live fixtures from individual leagues by league id

    Args:
        league_id (int): League id from API

    Returns:
        list[dict]: List of fixture dicts (from transform_fixture), not ORM objects
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
                previous_status = LIVE_MATCHES_STORE.get(fx["id"], (None,))[0]
                if matches_changed(fx["id"], fx):
                    await redis_client.publish(
                        "match-updates",
                        json.dumps(fx, default=str)
                    )
                    if fx["status"] == "finished" and previous_status != "finished":
                        league_id = fx["league_id"]
                        asyncio.create_task(poll_stages_then_stats(league_id))

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
            
async def poll_stages(league_id: int | None = None):
    """Check the current stage for each competition in LEAGUES, or just one
    league when triggered off a finished match.
    """
    print("Starting stages poll...")
    league_ids = [league_id] if league_id is not None else [details.get("bzzorio_id") for details in LEAGUES.values()]
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_current_stage(lid)) for lid in league_ids]
            
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

# SEED A LEAGUE'S FULL CURRENT SEASON (one-time per league, guarded — see poll_seed_missing_seasons)
async def seed_league_fixtures(league_id: int):
    """Backfill every fixture for a league's current season. Only meant to be
    called for a league that has none yet — poll_upcoming_matches only ever
    covers a rolling 7-day window, so without this a fresh DB (or a league
    just added to LEAGUES) would never get its past/full-season fixtures.
    """
    if not league_id:
        return
    try:
        season_fixtures = []
        fixtures_request = await client.get(f"events/", params={"league_id": league_id, "status": "upcoming", "date_from": current_season_start().strftime("%Y-%m-%d"), "limit": 10})
        fixtures_request.raise_for_status()

        while fixtures_request.status_code == 200:
            season_fixtures.extend([transform_fixture(fx) for fx in fixtures_request.json()["results"]])
            next_url = fixtures_request.json().get("next")
            if not next_url:
                break
            fixtures_request = await client.get(next_url)

        async with async_session() as db:
            await upsert_fixtures(db, season_fixtures)
        print(f"Seeded {len(season_fixtures)} fixtures for league {league_id}")
    except httpx.HTTPStatusError as e:
        print(f"API returned HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError) as e:
        print(f"Unexpected Error")

async def poll_seed_missing_seasons():
    """Backfills the full current season for any league that has nothing in
    the DB yet — a fresh DB, a new season, or a league just added to LEAGUES —
    and does nothing otherwise. Guarded so restarting the poller never
    re-triggers a full-season fetch for leagues that are already seeded.
    """
    league_ids = [details.get("bzzorio_id") for details in LEAGUES.values() if details.get("bzzorio_id")]
    async with async_session() as db:
        needs_seed = [lid for lid in league_ids if not await has_fixtures_for_season(db, lid)]

    if not needs_seed:
        return

    print(f"Seeding fixtures for leagues with no current-season data: {needs_seed}")
    async with asyncio.TaskGroup() as tg:
        for league_id in needs_seed:
            tg.create_task(seed_league_fixtures(league_id))

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
        
async def poll_standings(league_id: int | None = None):
    """Poll standings for every competition in LEAGUES, or just one league
    when triggered off a finished match.
    """
    print("Starting standings poll...")
    league_ids = [league_id] if league_id is not None else [details.get("bzzorio_id") for details in LEAGUES.values()]
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_standings(lid)) for lid in league_ids]
    
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
            
async def poll_stat(league_id: int | None = None):
    """Poll player stats across all competitions, or just one league when
    triggered off a finished match.
    """
    print("Starting stats poll...")
    league_ids = [league_id] if league_id is not None else [details.get("bzzorio_id") for details in LEAGUES.values()]
    async with asyncio.TaskGroup() as tg:
        requests = [tg.create_task(fetch_stat(lid)) for lid in league_ids]
        
    player_stats = []
    async with async_session() as db:
        for response in requests:
            stats = response.result()
            if not stats:
                continue
            player_stats.extend(stats)
            
        await upsert_stat(db, player_stats)
    print('Stats poll complete')

async def poll_stages_then_stats(league_id: int | None = None):
    """poll_standings/poll_stat both look up comp_stages (via get_current_stage)
    to resolve a season id — they need poll_stages to have actually finished
    writing that league's stage(s) first, not just be running concurrently
    with it. Firing all three as independent tasks races them: on a database
    that already has stage rows (any long-running local dev DB) the race is
    invisible, but on a genuinely empty one (a fresh deploy) poll_stages
    hasn't written anything yet and the other two reliably lose."""
    await poll_stages(league_id)
    asyncio.create_task(poll_standings(league_id))
    asyncio.create_task(poll_stat(league_id))

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_live_fixtures, "interval", seconds=30, id="live_fixtures")
    scheduler.add_job(poll_upcoming_matches, "interval", days=1, id="upcoming_matches", next_run_time=datetime.now())
    scheduler.start()

    asyncio.create_task(poll_seed_missing_seasons())
    asyncio.create_task(poll_stages_then_stats())

    print("POLLER UP")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    
if __name__ == "__main__":
    asyncio.run(main())