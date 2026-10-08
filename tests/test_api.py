from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.types.types import FixtureOut
from database.database import get_session
from database.repository import transform_fixture
from database.tables import CompetitionStages, Fixture, PlayerStat, Standing

LEAGUE_ID = 1
SEASON_ID = 1058
NOW = datetime.now(timezone.utc)
TODAY = NOW.date().isoformat()


@pytest_asyncio.fixture
async def client(test_db_session):
    async def override_get_session():
        yield test_db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def make_fixture(raw_fixture: dict, **overrides) -> Fixture:
    # Kicks off at NOW: always on TODAY and inside the current season, and
    # already started by the time any repository function reads the clock.
    # Anything earlier crosses into yesterday during the first hour of a UTC day.
    return Fixture(**transform_fixture({
        **raw_fixture,
        "event_date": NOW.isoformat(),
        **overrides,
    }))


def make_current_stage(league_id: int = LEAGUE_ID) -> CompetitionStages:
    return CompetitionStages(
        season_id=SEASON_ID,
        league_id=league_id,
        stage="regular-season",
        stage_name="Regular season",
        rounds=38,
        sort_order=0,
        start_date=NOW - timedelta(days=30),
        end_date=NOW + timedelta(days=200),
    )


def make_standing(team_id: int, position: int, season_id: int = SEASON_ID) -> Standing:
    return Standing(
        league_id=LEAGUE_ID, season_id=season_id, team_id=team_id, team_name=f"Team {team_id}",
        position=position, played=7, won=5, drawn=2, lost=0, gf=14, ga=4, gd=10, pts=17,
    )


def make_stat(player_id: int, rank: int, stat_type: str = "scorers") -> PlayerStat:
    return PlayerStat(
        league_id=LEAGUE_ID, season_id=SEASON_ID, stat_type=stat_type, rank=rank,
        player_id=player_id, player_name=f"Player {player_id}", player_position="F",
        team_id=42, team_name="Arsenal", value=6, matches=7,
    )


async def seed(db, rows: list) -> None:
    for row in rows:
        db.add(row)
        await db.flush()
    await db.commit()


async def test_health_check(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_round_matches_returns_fixture_shape(client, test_db_session, raw_fixture):
    await seed(test_db_session, [make_fixture(raw_fixture)])

    response = await client.get(f"/matches/{LEAGUE_ID}/round/{raw_fixture['round_number']}")

    assert response.status_code == 200
    body = response.json()
    assert [f["id"] for f in body] == [raw_fixture["id"]]
    assert body[0].keys() == FixtureOut.model_fields.keys()


async def test_league_date_matches_excludes_other_leagues(client, test_db_session, raw_fixture):
    await seed(test_db_session, [
        make_fixture(raw_fixture, id=1, league_id=LEAGUE_ID),
        make_fixture(raw_fixture, id=2, league_id=99),
    ])

    response = await client.get(f"/matches/{LEAGUE_ID}/date/{TODAY}")

    assert response.status_code == 200
    assert [f["id"] for f in response.json()] == [1]


async def test_date_matches_spans_all_leagues(client, test_db_session, raw_fixture):
    await seed(test_db_session, [
        make_fixture(raw_fixture, id=1, league_id=LEAGUE_ID),
        make_fixture(raw_fixture, id=2, league_id=99),
    ])

    response = await client.get(f"/matches/date/{TODAY}")
    assert response.status_code == 200
    assert {f["id"] for f in response.json()} == {1, 2}


async def test_current_round_for_unseeded_league_is_null(client):
    response = await client.get("/matches/99/current")

    assert response.status_code == 200
    assert response.json() is None


async def test_current_round_returns_stage_and_round(client, test_db_session, raw_fixture):
    await seed(test_db_session, [make_current_stage(), make_fixture(raw_fixture)])

    response = await client.get(f"/matches/{LEAGUE_ID}/current")

    assert response.status_code == 200
    assert response.json() == {
        "stage": "regular-season",
        "stage_name": "Regular season",
        "round_number": raw_fixture["round_number"],
    }


async def test_standings_for_unseeded_league_is_empty(client):
    # Used to 500: the route read .season_id off get_current_stage's None.
    response = await client.get("/standings/99")

    assert response.status_code == 200
    assert response.json() == []


async def test_standings_current_season_ordered_by_position(client, test_db_session):
    await seed(test_db_session, [
        make_current_stage(),
        make_standing(team_id=20, position=2),
        make_standing(team_id=10, position=1),
        make_standing(team_id=30, position=1, season_id=SEASON_ID - 1),
    ])

    response = await client.get(f"/standings/{LEAGUE_ID}")

    assert response.status_code == 200
    assert [row["team_id"] for row in response.json()] == [10, 20]


async def test_stats_for_unseeded_league_is_empty(client):
    response = await client.get("/stats/99/scorers")

    assert response.status_code == 200
    assert response.json() == []


async def test_stats_filtered_by_type_and_ordered_by_rank(client, test_db_session):
    await seed(test_db_session, [
        make_current_stage(),
        make_stat(player_id=2, rank=2),
        make_stat(player_id=1, rank=1),
        make_stat(player_id=3, rank=1, stat_type="assists"),
    ])

    response = await client.get(f"/stats/{LEAGUE_ID}/scorers")

    assert response.status_code == 200
    assert [row["player_id"] for row in response.json()] == [1, 2]


@pytest.mark.parametrize("path", [
    "/matches/abc/round/7",
    "/matches/1/round/abc",
    "/matches/abc/date/2026-10-04",
    "/matches/1/date/not-a-date",
    "/matches/date/2026-13-45",
    "/matches/abc/current",
    "/standings/abc",
    "/stats/abc/scorers",
])
async def test_malformed_path_params_return_422(client, path):
    # Used to 500: matches.py parsed these by hand inside the route body.
    response = await client.get(path)

    assert response.status_code == 422
