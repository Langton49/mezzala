from database.tables import Fixture
from database.repository import get_live_fixtures, get_matches_by_round, get_matches_by_id_date, get_matches_by_date, current_season_start, upsert_fixtures
from datetime import timedelta, datetime

MATCH_DAY = current_season_start() + timedelta(days=100)

def make_fixture(id: int, kickoff: datetime, **kwargs) -> dict:
    """
    Creates a fixture object with the given keyword arguments.
    
    Args:
        **kwargs: Arbitrary keyword arguments to set as attributes of the fixture.
        Accepted attributes include:
            - league_id
            - home_team_id
            - home_score
            - home_team
            - away_team_id
            - away_score
            - away_team
            - round_number
            - status
        
    Returns:
        A dict representing a fixture.
    """
    return {
        "id":id,
        "event_date":kickoff,
        "league_id":kwargs.get('league_id', 1),
        "home_team_id":kwargs.get('home_team_id', 1),
        "home_score":kwargs.get("home_score", 3),
        "home_team":kwargs.get('home_team', 'Team A'),
        "away_team_id":kwargs.get('away_team_id', 2),
        "away_score":kwargs.get("away_score", 0),
        "away_team":kwargs.get('away_team', 'Team B'),
        "round_number":kwargs.get('round_number', 1),
        "status":kwargs.get('status', 'notstarted'),
    }

def use_fixture(fixture_dict: dict) -> Fixture:
    return Fixture(**fixture_dict)

async def insert_in_order(test_db_session, fixtures: list[Fixture]):
    """
    Inserts the given fixtures into the database in the order they are provided.
    
    Args:
        test_db_session: The database session.
        fixtures: A list of fixture objects to be inserted.
    """
    for fixture in fixtures:
        test_db_session.add(fixture)
        await test_db_session.flush()
    await test_db_session.commit()
    
async def test_live_fixtures_ordering(test_db_session):
    """
    Test to ensure that the get_live_fixtures function returns fixtures in a stable order.
    
    This test creates fixtures with different event dates and league IDs, inserts them into the database,
    and then retrieves them using the get_live_fixtures function. It asserts that the returned fixtures are
    ordered first by event date and then by league ID then by fixture id.
    """
    
    # Different kickoff, same league
    fixture1 = make_fixture(1, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture2 = make_fixture(2, MATCH_DAY + timedelta(hours=1), league_id=1, status="inprogress")
    fixture3 = make_fixture(3, MATCH_DAY + timedelta(hours=2), league_id=1, status="inprogress")
    # Same kickoff, same league
    fixture4 = make_fixture(4, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture5 = make_fixture(5, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture6 = make_fixture(6, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    # Different kickoff, different league
    fixture7 = make_fixture(7, MATCH_DAY + timedelta(hours=2), league_id=4, status="inprogress")
    fixture8 = make_fixture(8, MATCH_DAY + timedelta(hours=4), league_id=5, status="inprogress")
    fixture9 = make_fixture(9, MATCH_DAY + timedelta(hours=5), league_id=3, status="inprogress")
    # Same kickoff, different league
    fixture10 = make_fixture(10, MATCH_DAY + timedelta(hours=1), league_id=3, status="inprogress")
    fixture11 = make_fixture(11, MATCH_DAY + timedelta(hours=1), league_id=5, status="inprogress")
    fixture12 = make_fixture(12, MATCH_DAY + timedelta(hours=1), league_id=4, status="inprogress")
    
    # Insert fixtures into the database in a specific order
    await insert_in_order(test_db_session, [use_fixture(fixture10), use_fixture(fixture8), use_fixture(fixture9), 
                                            use_fixture(fixture12), use_fixture(fixture11), use_fixture(fixture7), 
                                            use_fixture(fixture4), use_fixture(fixture6), use_fixture(fixture5), 
                                            use_fixture(fixture1), use_fixture(fixture2), use_fixture(fixture3)])
    
    # Retrieve live fixtures from the database
    live_fixtures = await get_live_fixtures(test_db_session)
    
    # Assert that the fixtures are returned in the correct order
    assert [f.id for f in live_fixtures] == [2,10,12,11,3,7,1,4,5,6,8,9]
    
async def test_live_fixture_ordering_after_poll(test_db_session):
    fixture1 = make_fixture(1, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture2 = make_fixture(2, MATCH_DAY + timedelta(hours=1), league_id=1, status="inprogress")
    fixture3 = make_fixture(3, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture4 = make_fixture(4, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture5 = make_fixture(5, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    fixture6 = make_fixture(6, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress")
    
    await insert_in_order(test_db_session, [use_fixture(fixture6), use_fixture(fixture4), 
                                            use_fixture(fixture5), use_fixture(fixture2), 
                                            use_fixture(fixture3), use_fixture(fixture1)])
    live_fixtures = await get_live_fixtures(test_db_session)
    before = [f.id for f in live_fixtures]
    
    fixture3 = make_fixture(3, MATCH_DAY + timedelta(hours=3), league_id=1, status="inprogress", home_score=1)
    await upsert_fixtures(test_db_session, [fixture3])
    test_db_session.expire_all()
    live_fixtures = await get_live_fixtures(test_db_session)
    after = [f.id for f in live_fixtures]
    
    assert before == after == [2, 1, 3, 4, 5, 6]