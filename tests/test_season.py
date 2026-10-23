from datetime import datetime, timedelta, timezone
import pytest
import database.repository as repository
from database.repository import current_season_start, has_fixtures_for_season, transform_fixture
from database.tables import Fixture

LEAGUE_ID = 1
OTHER_LEAGUE_ID = 2


def freeze_clock(monkeypatch, moment: datetime) -> None:
    # current_season_start calls datetime.now() through the repository module,
    # so that module's `datetime` is what has to be replaced.
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(repository, "datetime", FrozenDatetime)


@pytest.mark.parametrize("now, season_year", [
    (datetime(2027, 1, 15, tzinfo=timezone.utc), 2026),       # mid-season, after New Year
    (datetime(2027, 6, 30, 23, 59, tzinfo=timezone.utc), 2026),  # last minute of the season
    (datetime(2027, 7, 1, 0, 0, tzinfo=timezone.utc), 2027),     # first minute of the next
    (datetime(2026, 12, 31, tzinfo=timezone.utc), 2026),      # mid-season, before New Year
])
def test_season_starts_on_most_recent_july_first(monkeypatch, now, season_year):
    freeze_clock(monkeypatch, now)

    assert current_season_start() == datetime(season_year, 7, 1, tzinfo=timezone.utc)


def make_fixture(raw_fixture: dict, kickoff: datetime, **overrides) -> Fixture:
    return Fixture(**transform_fixture({**raw_fixture, "event_date": kickoff.isoformat(), **overrides}))


async def seed(db, rows: list) -> None:
    db.add_all(rows)
    await db.commit()


async def test_no_fixtures_means_no_season_data(test_db_session):
    assert await has_fixtures_for_season(test_db_session, LEAGUE_ID) is False


async def test_fixture_this_season_counts(test_db_session, raw_fixture):
    await seed(test_db_session, [make_fixture(raw_fixture, datetime.now(timezone.utc), league_id=LEAGUE_ID)])

    assert await has_fixtures_for_season(test_db_session, LEAGUE_ID) is True


async def test_fixture_from_previous_season_does_not_count(test_db_session, raw_fixture):
    last_season = current_season_start() - timedelta(days=1)
    await seed(test_db_session, [make_fixture(raw_fixture, last_season, league_id=LEAGUE_ID)])

    assert await has_fixtures_for_season(test_db_session, LEAGUE_ID) is False


async def test_other_leagues_fixtures_do_not_count(test_db_session, raw_fixture):
    await seed(test_db_session, [make_fixture(raw_fixture, datetime.now(timezone.utc), league_id=OTHER_LEAGUE_ID)])

    assert await has_fixtures_for_season(test_db_session, LEAGUE_ID) is False
