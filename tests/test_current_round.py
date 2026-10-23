from datetime import datetime, timedelta, timezone

from database.repository import get_current_round, transform_fixture
from database.tables import CompetitionStages, Fixture

LEAGUE_ID = 7
STAGE = "league-phase"

# get_current_round reads the real clock, so everything is placed relative to now.
NOW = datetime.now(timezone.utc)


def make_stage(stage: str = STAGE) -> CompetitionStages:
    return CompetitionStages(
        season_id=1, league_id=LEAGUE_ID, stage=stage, stage_name=stage.replace("-", " ").title(),
        rounds=8, sort_order=0, start_date=NOW - timedelta(days=60), end_date=NOW + timedelta(days=60),
    )


def make_fixture(raw_fixture: dict, fixture_id: int, round_number: int, kickoff: datetime, stage: str = STAGE) -> Fixture:
    return Fixture(**transform_fixture({
        **raw_fixture, "id": fixture_id, "league_id": LEAGUE_ID, "stage": stage,
        "round_number": round_number, "event_date": kickoff.isoformat(),
    }))


async def seed(db, rows: list) -> None:
    for row in rows:
        db.add(row)
        await db.flush()
    await db.commit()


async def test_no_current_stage_returns_none(test_db_session):
    assert await get_current_round(test_db_session, LEAGUE_ID) is None


async def test_returns_round_of_most_recent_kickoff(test_db_session, raw_fixture):
    await seed(test_db_session, [
        make_stage(),
        make_fixture(raw_fixture, 3, round_number=3, kickoff=NOW + timedelta(days=7)),
        make_fixture(raw_fixture, 1, round_number=1, kickoff=NOW - timedelta(days=14)),
        make_fixture(raw_fixture, 2, round_number=2, kickoff=NOW - timedelta(days=1)),
    ])

    current = await get_current_round(test_db_session, LEAGUE_ID)

    assert current == {"stage": STAGE, "stage_name": "League Phase", "round_number": 2}


async def test_nothing_kicked_off_falls_forward_to_soonest_upcoming(test_db_session, raw_fixture):
    # Later round inserted first, so this fails if upcoming fixtures aren't
    # ordered by kickoff.
    await seed(test_db_session, [
        make_stage(),
        make_fixture(raw_fixture, 6, round_number=6, kickoff=NOW + timedelta(days=10)),
        make_fixture(raw_fixture, 5, round_number=5, kickoff=NOW + timedelta(days=3)),
    ])

    current = await get_current_round(test_db_session, LEAGUE_ID)

    assert current["round_number"] == 5


async def test_stage_without_fixtures_has_no_round(test_db_session):
    await seed(test_db_session, [make_stage()])

    current = await get_current_round(test_db_session, LEAGUE_ID)

    assert current == {"stage": STAGE, "stage_name": "League Phase", "round_number": None}


async def test_fixtures_from_other_stages_are_ignored(test_db_session, raw_fixture):
    # A qualifier more recent than anything in the current stage must not win.
    await seed(test_db_session, [
        make_stage(),
        make_fixture(raw_fixture, 1, round_number=1, kickoff=NOW - timedelta(days=10)),
        make_fixture(raw_fixture, 99, round_number=3, kickoff=NOW - timedelta(days=1), stage="qualification-round-3"),
    ])

    current = await get_current_round(test_db_session, LEAGUE_ID)

    assert current["round_number"] == 1
