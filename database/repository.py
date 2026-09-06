from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tables import Fixture, News, Teams

async def upsert_fixture(db: AsyncSession, fixture_data: dict) -> Fixture:
    statement = insert(Fixture).values(**fixture_data)
    statement = statement.on_conflict_do_update(
        index_elements=['match_id'],
        set_={col: val for col, val in fixture_data.items() if col != "match_id"}
    )
    await db.execute(statement)
    await db.commit()
    result = await db.execute(select(Fixture).where(Fixture.match_id == fixture_data['match_id']))
    return result.scalar_one()

async def get_live_fixtures(db: AsyncSession) -> list[Fixture]:
    result = await db.execute(select(Fixture).where(Fixture.status == 'live'))
    return result.scalars().all()

async def get_matches_by_league(db: AsyncSession, league_id: int) -> list[Fixture]:
    result = await db.execute(select(Fixture).where(Fixture.league_id == league_id))
    return result.scalars().all()