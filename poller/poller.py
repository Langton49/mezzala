import requests
from config.settings import settings
from config.leagues import LEAGUES
from database.tables import Fixture, LiveFixture
from database.repository import upsert_fixture
from database.database import async_session
from datetime import datetime
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
    try:
        live_requests = requests.get(f"{settings.bzzorio_base_url}events/live/?league_id={league_id}", headers={
            "Authorization": f"Token {settings.bzzorio_api_key}"
        })
        
        live_requests.raise_for_status()
        live_response = live_requests.json()['events']
        live_fixtures = []
        for lvfx in live_response:
            live_fixtures.append(LiveFixture(**transform_live_fixture(lvfx)))
        return live_fixtures
        
    except requests.exceptions.Timeout:
        print("Request timed out")

    except requests.exceptions.ConnectionError:
        print("Could not connect to the API")

    except requests.exceptions.HTTPError as e:
        print(f"API returned HTTP {e.response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

async def fetch_league_fixtures(league_id: int) -> list[Fixture]:
    """Fetch upcoming league fixtures by league id

    Args:
        league_id (int): The league id associated with the desired league tied to id field in LEAGUES

    Returns:
        list[Fixture]: A list of the Fixture object for each response fixture from the API
    """
    try:
        fixture_request = requests.get(f"{settings.bzzorio_base_url}events/?league_id={league_id}&status=upcoming&date_from={datetime.now().strftime("%Y-%m-%d")}&limit=10", headers={
            "Authorization": f"Token {settings.bzzorio_api_key}"
        })
        
        fixture_request.raise_for_status()
        league_fixtures = fixture_request.json()["results"]
        model_fixtures = []
        for fx in league_fixtures:
            fixture = Fixture(**transform_fixture(fx))
            model_fixtures.append(fixture)
        return model_fixtures
    except requests.exceptions.Timeout:
        print("Request timed out")

    except requests.exceptions.ConnectionError:
        print("Could not connect to the API")

    except requests.exceptions.HTTPError as e:
        print(f"API returned HTTP {e.response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        
async def fetch_fixture(match_id: int) -> Fixture:
    """Fetch individual fixture by its id

    Args:
        match_id (int): Fixture id from API

    Returns:
        Fixture: Fixture object for postgres table
    """
    try:
        fixture_request = requests.get(f"{settings.bzzorio_base_url}events/{match_id}", headers={
            "Authorization": f"Token {settings.bzzorio_api_key}"
        })
        
        fixture_request.raise_for_status()
        fixture  = fixture_request.json()
        return Fixture(**transform_fixture(fixture))
    except requests.exceptions.Timeout:
        print("Request timed out")

    except requests.exceptions.ConnectionError:
        print("Could not connect to the API")

    except requests.exceptions.HTTPError as e:
        print(f"API returned HTTP {e.response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
async def fetch_standings(league_id: int) -> list[dict]:
    """Fetch the league table for a given leagues id

    Args:
        league_id (int): League id from the API

    Returns:
        list[dict]: List of each teams entry in the league table. Each dict contains team stats as well as position for the league table
    """
    try:
        standings_request = requests.get(f"{settings.bzzorio_base_url}leagues/{league_id}/standings", headers={
            "Authorization": f"Token {settings.bzzorio_api_key}"
        })
        standings_request.raise_for_status()
        
        standings = standings_request.json()['standings']
        return standings
    except requests.exceptions.Timeout:
        print("Request timed out")

    except requests.exceptions.ConnectionError:
        print("Could not connect to the API")

    except requests.exceptions.HTTPError as e:
        print(f"API returned HTTP {e.response.status_code}")

    except requests.exceptions.RequestException as e:
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
        stat_request = requests.get(f"{settings.bzzorio_base_url}leagues/{league_id}/top/{stat}", headers={
            "Authorization": f"Token {settings.bzzorio_api_key}"
        })
        stat_request.raise_for_status()
        stats = stat_request.json()['leaders']
        print(stats)
    except requests.exceptions.Timeout:
        print("Request timed out")

    except requests.exceptions.ConnectionError:
        print("Could not connect to the API")

    except requests.exceptions.HTTPError as e:
        print(f"API returned HTTP {e.response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


