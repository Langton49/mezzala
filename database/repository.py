from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from .tables import Fixture, News, Team
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