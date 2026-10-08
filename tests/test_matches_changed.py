from poller.poller import matches_changed, LIVE_MATCHES_STORE
import pytest

@pytest.fixture(autouse=True)
def empty_store():
    LIVE_MATCHES_STORE.clear()
    yield
    LIVE_MATCHES_STORE.clear()
    
def test_matches_changed(raw_fixture):
    assert matches_changed(fixture_id=raw_fixture['id'], fixture_data=raw_fixture)
    assert not matches_changed(fixture_id=raw_fixture['id'], fixture_data=raw_fixture)
    assert not matches_changed(fixture_id=raw_fixture['id'], fixture_data={**raw_fixture, "home_coach_id": 1967})
    
@pytest.mark.parametrize("field, new_value", [
    ("status", "inprogress"),
    ("home_score", 3),
    ("away_score", 2),
    ("current_minute", 95),
])
def test_changed_fields(raw_fixture, field, new_value):
    changed = {**raw_fixture, field: new_value}
    matches_changed(fixture_id=raw_fixture["id"], fixture_data=raw_fixture)
    assert matches_changed(fixture_id=raw_fixture["id"], fixture_data=changed)
    assert not matches_changed(fixture_id=raw_fixture["id"], fixture_data=changed)
