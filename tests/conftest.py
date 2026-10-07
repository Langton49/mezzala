import os
from pathlib import Path
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.tables import Base
from dotenv import load_dotenv
import pytest

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TEST_DB_URL = f"postgresql+asyncpg://{os.environ.get('POSTGRES_USER', 'fake')}:{os.environ.get('POSTGRES_PASS', 'fake')}@{os.environ.get('TEST_DB_HOST', 'localhost')}:{os.environ.get('TEST_DB_PORT', '5432')}/mezzala_test"

@pytest_asyncio.fixture
async def test_db_session(): 
    ENGINE = create_async_engine(TEST_DB_URL, future=True) 
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(ENGINE, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await ENGINE.dispose()

@pytest.fixture
def raw_fixture():
    return {
        "id": 4193052,
        "league_id": 1,
        "season_id": 1058,
        "home_team_id": 42,
        "home_team": "Arsenal",
        "away_team_id": 50,
        "away_team": "Chelsea",
        "home_coach_id": 1964,
        "away_coach_id": 2278,
        "referee_id": 331,
        "venue_id": 494,
        "event_date": "2026-10-04T15:30:00+00:00",
        "status": "finished",
        "replaced_by": None,
        "round_number": 7,
        "round_name": "",
        "group_name": None,
        "stage": "regular-season",
        "stage_name": "Regular season",
        "round_label": "Regular season · Matchday 7",
        "period": "FT",
        "current_minute": 94,
        "home_score": 2,
        "away_score": 1,
        "home_score_ht": 1,
        "away_score_ht": 0,
        "penalty_shootout": None,
        "extra_time_score": None,
        "is_local_derby": True,
        "is_neutral_ground": False,
        "travel_distance_km": 12,
        "weather": {
            "code": 1,
            "description": "clear",
            "wind_speed": 8.3,
            "temperature_c": 18,
        },
        "pitch_condition": 1,
        "attendance": 60260,
        "live_websocket": True,
        "websocket_plus": True,
        "highlights": [
            {
                "kind": "full",
                "title": "Arsenal 2 - 1 Chelsea — Full Highlights",
                "url": "https://www.youtube.com/watch?v=abc123",
                "thumbnail": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
                "published_at": "2026-10-04T18:10:00+00:00",
            }
        ],
        "head_to_head": {
            "total_matches": 10,
            "home_wins": 4,
            "draws": 3,
            "away_wins": 3,
            "home_goals": 14,
            "away_goals": 11,
            "avg_total_goals": 2.5,
            "home_win_rate": 0.4,
            "away_win_rate": 0.3,
            "recent_matches": [
                {
                    "away": "Chelsea",
                    "date": "2026-10-04T15:30:00+00:00",
                    "home": "Arsenal",
                    "score": "2-1",
                    "event_id": 4193052,
                    "away_score": 1,
                    "home_score": 2,
                    "away_team_id": 50,
                    "home_team_id": 42,
                }
            ],
        },
        "has_xg": True,
        "previous_leg_event_id": None,
    }
    