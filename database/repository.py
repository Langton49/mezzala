from sqlalchemy import select, union, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from .tables import Fixture, CompetitionStages, Standing, PlayerStat, Team, Player, FIXTURE_COLS
from datetime import datetime, timezone, timedelta, date

# HELPERS
def transform_fixture(dictionary: dict) -> dict:
    res = {k: v for k, v in dictionary.items() if k in FIXTURE_COLS}
    if "event_date" in res:
        res["event_date"] = datetime.fromisoformat(res["event_date"])
    last_updated = dictionary.get("last_updated")
    res["last_updated"] = datetime.fromisoformat(last_updated) if last_updated else datetime.now(timezone.utc)
    return res
    
def transform_stage(dictionary: dict, league_id: int, season_id: int, sort_order: int) -> dict:
    # league_id and sort_order aren't on the raw stage object at all — league_id comes
    # from whichever league's /season/ response we're processing, and sort_order is the
    # stage's position in that response's `stages` array (bzzorio doesn't send an index).
    return {
        "season_id": season_id,
        "league_id": league_id,
        "stage": dictionary["stage"],
        "stage_name": dictionary["stage_name"],
        "rounds": dictionary["rounds"],
        "sort_order": sort_order,
        "start_date": datetime.fromisoformat(dictionary["start_date"]).replace(tzinfo=timezone.utc),
        "end_date": datetime.fromisoformat(dictionary["end_date"]).replace(tzinfo=timezone.utc),
    }
    
def transform_stat(stats: list[dict], league_id: int, curr_season: int, stat_type: str) -> list[dict]:
    result = []
    for rank in stats:
        result.append({
            'league_id': league_id,
            'season_id': curr_season,
            'stat_type': stat_type,
            'rank': rank['rank'],
            'player_id': rank['player_id'],
            'player_name': rank['player_name'],
            'player_position': rank['position'],
            'team_id': rank['team_id'],
            'team_name': rank['team_name'],
            'value': rank['value'],
            'matches': rank['matches']
        })
    return result
    
def transform_standings(standings: list[dict], league_id: int, curr_season: int) -> list[dict]:
    result = []
    for pos in standings:
        zone = pos.get('zone')
        result.append({
            'league_id': league_id,
            'season_id': curr_season,
            'team_id': pos['team_id'],
            'team_name': pos['team_name'],
            'position': pos['position'],
            'played': pos['played'],
            'won': pos['won'],
            'drawn': pos['drawn'],
            'lost': pos['lost'],
            'gf': pos['gf'],
            'ga': pos['ga'],
            'gd': pos['gd'],
            'pts': pos['pts'],
            'xgf': pos.get('xgf'),
            'xga': pos.get('xga'),
            'xgd': pos.get('xgd'),
            'form': pos.get('form'),
            'zone_key': zone['key'] if zone else None,
            'zone_label': zone['label'] if zone else None,
            'zone_type': zone['type'] if zone else None,
        })
    return result

def transform_team(team: dict, is_national: bool):
    return {
        'id': team['id'],
        'name': team['name'],
        'short_name': team.get('short_name') or None,
        'country': team.get('country') or None,
        'venue_id': team['venue_id'],
        'is_national': is_national
    }
    
def transform_player(player: dict):
    return {
        'id': player['id'],
        'name': player['name'],
        'position': player['position'],
        'role': player['specific_position'],
        'number': player['jersey_number'],
        'dob': date.fromisoformat(player['date_of_birth']) if player['date_of_birth'] else None,
        'height_cm': player['height_cm'],
        'preferred_foot': player['preferred_foot'],
        'nationality': player['nationality'],
        'current_team_id': (player.get('current_team') or {}).get('id', None),
        'national_team_id': (player.get('national_team') or {}).get('id', None),
        'market_value_eur': player['market_value_eur'],
        'contract_exp': date.fromisoformat(player['contract_until']) if player['contract_until'] else None,
        'availability': player['availability'],
        'injury_type': player['injury_type'],
        'injury_return': date.fromisoformat(player['injury_expected_return']) if player['injury_expected_return'] else None,
        'rating': player['rating'],
        'annual_wages_eur': player['wage_eur_annual']
    }
 
def current_season_start() -> datetime:
    """Beginning of the current football season (July 1). Football seasons span a
    calendar-year boundary (e.g. Aug 2026 - May 2027), so from January-June this
    must resolve back to July 1 of the *previous* year, not the current one."""
    now = datetime.now(timezone.utc)
    year = now.year if now.month >= 7 else now.year - 1
    return datetime(year, 7, 1, tzinfo=timezone.utc)

async def has_fixtures_for_season(db: AsyncSession, league_id: int) -> bool:
    """Whether any fixture is already stored for this league's current season —
    the guard that keeps the full-season backfill a one-time-per-season thing
    instead of something that redoes itself on every poller restart."""
    result = await db.execute(
        select(Fixture.id)
        .where(Fixture.league_id == league_id)
        .where(Fixture.event_date >= current_season_start())
        .limit(1)
    )
    return result.scalar() is not None

async def get_current_stage(db: AsyncSession, league_id: int) -> CompetitionStages | None:
    now = datetime.now(timezone.utc)

    # the common case: "now" falls inside some stage's span
    res = await db.execute(
        select(CompetitionStages)
        .where(CompetitionStages.league_id == league_id)
        .where(CompetitionStages.start_date <= now)
        .where(CompetitionStages.end_date >= now)
        .order_by(CompetitionStages.start_date.asc(), CompetitionStages.id.asc())
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
        .order_by(CompetitionStages.start_date.asc(), CompetitionStages.id.asc())
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

# UPSERT FUNCTIONS
async def upsert_fixtures(db: AsyncSession, fixture_data: list[dict]) -> Fixture:
    for fixture in fixture_data:
        statement = insert(Fixture).values(**fixture)
        statement = statement.on_conflict_do_update(
            index_elements=['id'],
            set_={col: val for col, val in fixture.items() if col != "id"}
        )
        await db.execute(statement)
        await db.commit()

async def upsert_stages(db: AsyncSession, stages: list[dict]):
    for stage in stages:
        statement = insert(CompetitionStages).values(**stage)
        statement = statement.on_conflict_do_update(
            index_elements=['league_id', 'stage'],
            set_={col: val for col, val in stage.items() if col != "id"}
        )
        await db.execute(statement)
        await db.commit()
        
async def upsert_standings(db: AsyncSession, standings: list[dict]):
    for pos in standings:
        statement = insert(Standing).values(**pos)
        statement = statement.on_conflict_do_update(
            index_elements=['league_id', 'season_id', 'team_id'],
            set_={col: val for col, val in pos.items()}
        )
        await db.execute(statement)
        await db.commit()

async def upsert_stat(db: AsyncSession, stats: list[dict]):
    for ranking in stats:
        statement = insert(PlayerStat).values(**ranking)
        statement = statement.on_conflict_do_update(
            index_elements=["league_id", "season_id", "stat_type", "player_id"],
            set_={col: val for col, val in ranking.items()}
        )
        await db.execute(statement)
        await db.commit()
        
async def upsert_team(db: AsyncSession, teams: list[dict]):
    for team in teams:
        statement = insert(Team).values(**team)
        statement = statement.on_conflict_do_update(
                    index_elements=["id"],
                    set_={col: val for col, val in team.items()}
                )
        await db.execute(statement)
        await db.commit()
        
async def upsert_players(db: AsyncSession, players: list[dict]):
    for player in players:
        statement = insert(Player).values(**player)
        statement = statement.on_conflict_do_update(
            index_elements=['id'],
            set_={col: val for col, val in player.items()}
        )
        await db.execute(statement)
        await db.commit()

# ENDPOINT FUNCTIONS
async def get_live_fixtures(db: AsyncSession) -> list[Fixture]:
    """Get live matches via websocket
    
    Args:
        db (AsyncSession): Db connection
        
    Returns:
        list[Fixtures]: List of all live fixtures
    """
    result = await db.execute(select(Fixture)
                              .where(Fixture.status == 'inprogress')
                              .order_by(Fixture.event_date.asc(), Fixture.league_id.asc(), Fixture.id.asc()))
    return result.scalars().all()

async def get_matches_by_round(db: AsyncSession, league_id: int, stage: str, round: int) -> list[Fixture]:
    """Get league matches by round/matchday

    Args:
        db (AsyncSession): Db connection
        league_id (int): Competition id
        stage: Competition stage
        round (int): Competition round

    Returns:
        list[Fixture]: List of fixtures in the round
    """
    result = await db.execute(
        select(Fixture)
        .where(Fixture.league_id == league_id)
        .where(Fixture.round_number == round)
        .where(Fixture.stage == stage)
        .where(Fixture.event_date >= current_season_start())
        .order_by(Fixture.event_date.asc(), Fixture.id.asc())
    )
    return result.scalars().all()

async def get_matches_by_id_date(db: AsyncSession, league_id: int, date: datetime) -> list[Fixture]:
    """Get league matches by their kickoff time 

    Args:
        db (AsyncSession): Db connection
        league_id (int): Competition id
        date (datetime): Specific date for the kickoff, turns to one day range to account for all fixtures that day

    Returns:
        list[Fixture]: List of fixtures on date
    """
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(select(Fixture)
                              .where(Fixture.league_id == league_id)
                              .where(Fixture.event_date >= day_start)
                              .where(Fixture.event_date < day_end)
                              .order_by(Fixture.event_date.asc(), Fixture.id.asc()))
    return result.scalars().all()

async def get_matches_by_date(db: AsyncSession, date: datetime) -> list[Fixture]:
    """Get matches for specific day for all competitions

    Args:
        db (AsyncSession): Db connection
        date (datetime): Specific date for the kickoff, turns to one day range to account for all fixtures that day

    Returns:
        list[Fixture]: List of all fixtures across all leagues on date
    """
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(select(Fixture)
                            .where(Fixture.event_date >= day_start)
                            .where(Fixture.event_date < day_end)
                            .order_by(Fixture.event_date.asc(), Fixture.league_id.asc(), Fixture.id.asc()))
    return result.scalars().all()    

async def get_missing_teams(db: AsyncSession) -> list[tuple[int, bool]]:
    home = select(Fixture.home_team_id.label("team_id"), Fixture.league_id)
    away = select(Fixture.away_team_id.label("team_id"), Fixture.league_id)
    pairs = union(home, away).subquery()
    
    result = await db.execute(
        select(pairs.c.team_id, func.bool_or(pairs.c.league_id == 64))
        .where(pairs.c.team_id.not_in(select(Team.id)))
        .group_by(pairs.c.team_id)
    )
    return result.all()

async def get_all_team_id(db: AsyncSession):
    statement = select(Team.id).where(Team.is_national == False)
    result = await db.execute(statement)
    return result.scalars().all()
            
async def get_standings(db: AsyncSession, league_id: int, curr_season: int) -> list[Standing]:
    """Get current standings for a competition. Data source needs season id for current season's standings

    Args:
        db (AsyncSession): Db connection
        league_id (int): Competition id
        curr_season (int): Current season id

    Returns:
        list[Standing]: List of the individual positions of each team in the league's standings
    """
    results = await db.execute(select(Standing)
                               .where(Standing.league_id == league_id)
                               .where(Standing.season_id == curr_season)
                               .order_by(Standing.position.asc()))
    return results.scalars().all()
        
async def get_stat(db: AsyncSession, league_id: int, curr_season: int, stat: str) -> list[PlayerStat]:
    """Get player stats for a given league and stat

    Args:
        db (AsyncSession): Db connection
        league_id (int): Competition id
        curr_season (int): Current season id
        stat (str): Required player statistic

    Returns:
        list[PlayerStat]: List of all player positions for that league and stat
    """
    results = await db.execute(select(PlayerStat)
                               .where(PlayerStat.league_id == league_id)
                               .where(PlayerStat.season_id == curr_season)
                               .where(PlayerStat.stat_type == stat)
                               .order_by(PlayerStat.rank.asc()))
    return results.scalars().all()