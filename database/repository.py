from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from .tables import Fixture, News, Team, CompetitionStages
from sqlalchemy import inspect
from datetime import datetime, timezone, timedelta

def transform_fixture(dictionary: dict) -> dict:
    last_updated = dictionary.get("last_updated")
    return {
        "id": dictionary["id"],
        "league_id": dictionary["league_id"],
        "home_team_id": dictionary["home_team_id"],
        "home_team": dictionary["home_team"],
        "home_coach_id": dictionary.get("home_coach_id"),
        "away_team_id": dictionary["away_team_id"],
        "away_team": dictionary["away_team"],
        "away_coach_id": dictionary.get("away_coach_id"),
        "referee_id": dictionary.get("referee_id"),
        "round_number": dictionary.get("round_number"),
        "round_name": dictionary.get("round_name"),
        "group_name": dictionary.get("group_name"),
        "stage": dictionary.get("stage"),
        "stage_name": dictionary.get("stage_name"),
        "venue_id": dictionary.get("venue_id"),
        "event_date": datetime.fromisoformat(dictionary["event_date"]),
        "status": dictionary["status"],
        "home_score": dictionary.get("home_score"),
        "away_score": dictionary.get("away_score"),
        "current_minute": dictionary.get("current_minute"),
        "home_score_ht": dictionary.get("home_score_ht"),
        "away_score_ht": dictionary.get("away_score_ht"),
        # bzzorio never sends this field, only the poller's fabricated test_fixture_data does —
        # treat it as optional and stamp our own ingestion time when it's missing.
        "last_updated": datetime.fromisoformat(last_updated) if last_updated else datetime.now(timezone.utc)
    }

def transform_stage(dictionary: dict, league_id: int, sort_order: int) -> dict:
    # league_id and sort_order aren't on the raw stage object at all — league_id comes
    # from whichever league's /season/ response we're processing, and sort_order is the
    # stage's position in that response's `stages` array (bzzorio doesn't send an index).
    return {
        "league_id": league_id,
        "stage": dictionary["stage"],
        "stage_name": dictionary["stage_name"],
        "rounds": dictionary["rounds"],
        "sort_order": sort_order,
        "start_date": datetime.fromisoformat(dictionary["start_date"]).replace(tzinfo=timezone.utc),
        "end_date": datetime.fromisoformat(dictionary["end_date"]).replace(tzinfo=timezone.utc),
    }

async def upsert_fixture(db: AsyncSession, fixture_data: dict) -> Fixture:
    statement = insert(Fixture).values(**fixture_data)
    statement = statement.on_conflict_do_update(
        index_elements=['id'],
        set_={col: val for col, val in fixture_data.items() if col != "id"}
    )
    await db.execute(statement)
    await db.commit()
    # result = await db.execute(select(Fixture).where(Fixture.id == fixture_data['id']))
    # return result.scalar_one()

async def upsert_batch(db: AsyncSession, fixtures: list[Fixture]):
    for fixture in fixtures:
        await upsert_fixture(db, fixture)
    print(f"Completed")

async def get_live_fixtures(db: AsyncSession) -> list[Fixture]:
    result = await db.execute(select(Fixture).where(Fixture.status == 'live'))
    return result.scalars().all()

def current_season_start() -> datetime:
    """Beginning of the current football season (July 1). Football seasons span a
    calendar-year boundary (e.g. Aug 2026 - May 2027), so from January-June this
    must resolve back to July 1 of the *previous* year, not the current one."""
    now = datetime.now(timezone.utc)
    year = now.year if now.month >= 7 else now.year - 1
    return datetime(year, 7, 1, tzinfo=timezone.utc)

async def get_current_stage(db: AsyncSession, league_id: int) -> CompetitionStages | None:
    now = datetime.now(timezone.utc)

    # the common case: "now" falls inside some stage's span
    res = await db.execute(
        select(CompetitionStages)
        .where(CompetitionStages.league_id == league_id)
        .where(CompetitionStages.start_date <= now)
        .where(CompetitionStages.end_date >= now)
    )
    stage = res.scalars().first()
    if stage:
        return stage

    # gap between two stages (e.g. playoff-round has ended, league-phase hasn't
    # started yet) — fall forward to whichever stage starts soonest
    res = await db.execute(
        select(CompetitionStages)
        .where(CompetitionStages.league_id == league_id)
        .where(CompetitionStages.start_date > now)
        .order_by(CompetitionStages.start_date.asc())
    )
    stage = res.scalars().first()
    if stage:
        return stage

    # nothing upcoming either (season's over, or comp_stages hasn't been synced
    # for the new season yet) — fall back to whatever ended most recently
    res = await db.execute(
        select(CompetitionStages)
        .where(CompetitionStages.league_id == league_id)
        .order_by(CompetitionStages.end_date.desc())
    )
    return res.scalars().first()

async def get_current_round(db: AsyncSession, league_id: int) -> dict | None:
    """Resolve which stage AND which round within it is "current" for a league.

    comp_stages only knows a stage's overall span, not per-round dates, so
    finding the round still requires a second lookup against fixtures.
    """
    stage = await get_current_stage(db, league_id)
    if stage is None:
        return None

    now = datetime.now(timezone.utc)

    # most recent fixture in this stage that's already kicked off
    res = await db.execute(
        select(Fixture)
        .where(Fixture.league_id == league_id)
        .where(Fixture.stage == stage.stage)
        .where(Fixture.event_date <= now)
        .order_by(Fixture.event_date.desc())
    )
    fixture = res.scalars().first()

    if fixture is None:
        # nothing in this stage has started yet — take the soonest upcoming one
        res = await db.execute(
            select(Fixture)
            .where(Fixture.league_id == league_id)
            .where(Fixture.stage == stage.stage)
            .where(Fixture.event_date > now)
            .order_by(Fixture.event_date.asc())
        )
        fixture = res.scalars().first()

    return {
        "stage": stage.stage,
        "stage_name": stage.stage_name,
        "round_number": fixture.round_number if fixture else None,
    }

async def get_matches_by_round(db: AsyncSession, league_id: int, round: int) -> list[Fixture]:
    """Get league matches by round/matchday

    Args:
        db (AsyncSession): _description_
        league_id (int): _description_
        round (int): _description_

    Returns:
        list[Fixture]: _description_
    """
    result = await db.execute(
        select(Fixture)
        .where(Fixture.league_id == league_id)
        .where(Fixture.round_number == round)
        .where(Fixture.event_date >= current_season_start())
    )
    return result.scalars().all()

async def get_matches_by_id_date(db: AsyncSession, league_id: int, date: datetime) -> list[Fixture]:
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(select(Fixture)
                              .where(Fixture.league_id == league_id)
                              .where(Fixture.event_date >= day_start)
                              .where(Fixture.event_date < day_end))
    return result.scalars().all()

async def get_matches_by_date(db: AsyncSession, date: datetime) -> list[Fixture]:
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(select(Fixture)
                            .where(Fixture.event_date >= day_start)
                            .where(Fixture.event_date < day_end))
    return result.scalars().all()    
    
def orm_to_dict(obj) -> dict:
    return {col.key: getattr(obj, col.key) for col in inspect(obj).mapper.column_attrs}

async def upsert_stage(db: AsyncSession, stage: dict):
    statement = insert(CompetitionStages).values(**stage)
    statement = statement.on_conflict_do_update(
        index_elements=['league_id', 'stage'],
        set_={col: val for col, val in stage.items() if col != "id"}
    )
    await db.execute(statement)
    await db.commit()