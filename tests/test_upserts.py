from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from database.repository import (
    transform_fixture,
    upsert_fixtures,
    upsert_stages,
    upsert_standings,
    upsert_stat,
)
from database.tables import CompetitionStages, Fixture, PlayerStat, Standing

SEASON_START = datetime(2026, 8, 21, tzinfo=timezone.utc)

STAGE_ROW = {
    "season_id": 1058, "league_id": 1, "stage": "regular-season", "stage_name": "Regular season",
    "rounds": 38, "sort_order": 0, "start_date": SEASON_START, "end_date": SEASON_START + timedelta(days=280),
}

STANDING_ROW = {
    "league_id": 1, "season_id": 1058, "team_id": 42, "team_name": "Arsenal", "position": 1,
    "played": 7, "won": 5, "drawn": 2, "lost": 0, "gf": 14, "ga": 4, "gd": 10, "pts": 17,
    "xgf": 13.2, "xga": 5.1, "xgd": 8.1, "form": "WWDWW",
    "zone_key": "cl", "zone_label": "Champions League", "zone_type": "qualification",
}

STAT_ROW = {
    "league_id": 1, "season_id": 1058, "stat_type": "scorers", "rank": 1, "player_id": 852,
    "player_name": "J. Smith", "player_position": "F", "team_id": 42, "team_name": "Arsenal",
    "value": 6, "matches": 7,
}


async def all_rows(db, model) -> list:
    # Upserts are Core statements, so the session's cached objects go stale.
    db.expire_all()
    return list((await db.execute(select(model))).scalars())


async def row_count(db, model) -> int:
    return await db.scalar(select(func.count()).select_from(model))


async def test_upsert_fixtures_updates_on_id_conflict(test_db_session, raw_fixture):
    fixture = transform_fixture(raw_fixture)
    await upsert_fixtures(test_db_session, [fixture])

    await upsert_fixtures(test_db_session, [{**fixture, "home_score": 3, "current_minute": 95}])

    rows = await all_rows(test_db_session, Fixture)
    assert len(rows) == 1
    assert (rows[0].home_score, rows[0].current_minute) == (3, 95)


async def test_upsert_fixtures_inserts_every_item_in_the_list(test_db_session, raw_fixture):
    first = transform_fixture(raw_fixture)
    second = transform_fixture({**raw_fixture, "id": raw_fixture["id"] + 1})

    await upsert_fixtures(test_db_session, [first, second])

    assert await row_count(test_db_session, Fixture) == 2


async def test_upsert_stages_conflicts_on_league_and_stage(test_db_session):
    await upsert_stages(test_db_session, [STAGE_ROW])
    await upsert_stages(test_db_session, [{**STAGE_ROW, "rounds": 40}])

    rows = await all_rows(test_db_session, CompetitionStages)
    assert len(rows) == 1
    assert rows[0].rounds == 40

    await upsert_stages(test_db_session, [{**STAGE_ROW, "league_id": 2}])

    assert await row_count(test_db_session, CompetitionStages) == 2


async def test_upsert_standings_conflicts_on_league_season_and_team(test_db_session):
    await upsert_standings(test_db_session, [STANDING_ROW])
    await upsert_standings(test_db_session, [{**STANDING_ROW, "position": 2, "pts": 18}])

    rows = await all_rows(test_db_session, Standing)
    assert len(rows) == 1
    assert (rows[0].position, rows[0].pts) == (2, 18)

    await upsert_standings(test_db_session, [{**STANDING_ROW, "season_id": 1059}])

    assert await row_count(test_db_session, Standing) == 2


async def test_upsert_stat_conflicts_on_league_season_type_and_player(test_db_session):
    await upsert_stat(test_db_session, [STAT_ROW])
    await upsert_stat(test_db_session, [{**STAT_ROW, "value": 7, "rank": 2}])

    rows = await all_rows(test_db_session, PlayerStat)
    assert len(rows) == 1
    assert (rows[0].value, rows[0].rank) == (7, 2)

    # Same player, different leaderboard: a separate row, not an overwrite.
    await upsert_stat(test_db_session, [{**STAT_ROW, "stat_type": "assists"}])

    assert await row_count(test_db_session, PlayerStat) == 2
