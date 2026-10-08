from datetime import datetime, timedelta, timezone
from database.repository import get_current_stage
from database.tables import CompetitionStages

LEAGUE_ID = 7
OTHER_LEAGUE_ID = 8

# get_current_stage reads the real clock, so every stage is placed relative to
# now rather than on fixed dates.
NOW = datetime.now(timezone.utc)


def make_stage(stage: str, starts_in_days: int, ends_in_days: int, league_id: int = LEAGUE_ID) -> CompetitionStages:
    return CompetitionStages(
        season_id=1,
        league_id=league_id,
        stage=stage,
        stage_name=stage.replace("-", " ").title(),
        rounds=6,
        sort_order=0,
        start_date=NOW + timedelta(days=starts_in_days),
        end_date=NOW + timedelta(days=ends_in_days),
    )


async def insert_in_order(db, stages: list[CompetitionStages]) -> None:
    for stage in stages:
        db.add(stage)
        await db.flush()
    await db.commit()


async def test_returns_stage_spanning_now(test_db_session):
    await insert_in_order(test_db_session, [
        make_stage("qualifying", -60, -31),
        make_stage("league-phase", -30, 30),
        make_stage("knockout", 31, 90),
    ])

    stage = await get_current_stage(test_db_session, LEAGUE_ID)

    assert stage.stage == "league-phase"


async def test_between_stages_falls_forward_to_soonest_upcoming(test_db_session):
    # Later-starting stage inserted first, so this fails if the upcoming
    # stages aren't ordered by start date.
    await insert_in_order(test_db_session, [
        make_stage("final", 60, 61),
        make_stage("playoff-round", -30, -1),
        make_stage("knockout", 5, 50),
    ])

    stage = await get_current_stage(test_db_session, LEAGUE_ID)

    assert stage.stage == "knockout"


async def test_nothing_upcoming_falls_back_to_most_recently_ended(test_db_session):
    # Older stage inserted first, so this fails if ended stages aren't
    # ordered by end date.
    await insert_in_order(test_db_session, [
        make_stage("league-phase", -300, -200),
        make_stage("final", -20, -10),
    ])

    stage = await get_current_stage(test_db_session, LEAGUE_ID)

    assert stage.stage == "final"


async def test_no_stages_returns_none(test_db_session):
    assert await get_current_stage(test_db_session, LEAGUE_ID) is None


async def test_ignores_other_leagues(test_db_session):
    await insert_in_order(test_db_session, [
        make_stage("league-phase", -30, 30, league_id=OTHER_LEAGUE_ID),
        make_stage("final", -20, -10),
    ])

    stage = await get_current_stage(test_db_session, LEAGUE_ID)

    assert stage.stage == "final"
    assert stage.league_id == LEAGUE_ID
