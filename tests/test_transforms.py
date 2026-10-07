from datetime import datetime, timedelta, timezone

import pytest

from database.repository import transform_stat, transform_standings, transform_stage, transform_fixture

RAW_FIXTURE = {
    "id": 4193052,
    "league_id": 1,
    "season_id": 1058,
    "home_team_id": 42,
    "home_team": "Arsenal",
    "away_team_id": 50,
    "away_team": "Chelsea",
    "home_coach_id": 1964,
    "away_coach_id": 2278,
    "referee_id": 331,
    "venue_id": 494,
    "event_date": "2026-10-04T15:30:00+00:00",
    "status": "finished",
    "replaced_by": None,
    "round_number": 7,
    "round_name": "",
    "group_name": None,
    "stage": "regular-season",
    "stage_name": "Regular season",
    "round_label": "Regular season · Matchday 7",
    "period": "FT",
    "current_minute": 94,
    "home_score": 2,
    "away_score": 1,
    "home_score_ht": 1,
    "away_score_ht": 0,
    "penalty_shootout": None,
    "extra_time_score": None,
    "is_local_derby": True,
    "is_neutral_ground": False,
    "travel_distance_km": 12,
    "weather": {
        "code": 1,
        "description": "clear",
        "wind_speed": 8.3,
        "temperature_c": 18,
    },
    "pitch_condition": 1,
    "attendance": 60260,
    "live_websocket": True,
    "websocket_plus": True,
    "highlights": [
        {
            "kind": "full",
            "title": "Arsenal 2 - 1 Chelsea — Full Highlights",
            "url": "https://www.youtube.com/watch?v=abc123",
            "thumbnail": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
            "published_at": "2026-10-04T18:10:00+00:00",
        }
    ],
    "head_to_head": {
        "total_matches": 10,
        "home_wins": 4,
        "draws": 3,
        "away_wins": 3,
        "home_goals": 14,
        "away_goals": 11,
        "avg_total_goals": 2.5,
        "home_win_rate": 0.4,
        "away_win_rate": 0.3,
        "recent_matches": [
            {
                "away": "Chelsea",
                "date": "2026-10-04T15:30:00+00:00",
                "home": "Arsenal",
                "score": "2-1",
                "event_id": 4193052,
                "away_score": 1,
                "home_score": 2,
                "away_team_id": 50,
                "home_team_id": 42,
            }
        ],
    },
    "has_xg": True,
    "previous_leg_event_id": None,
}

RAW_STATS = [{
    "rank": 1,
    "player_id": 852,
    "player_name": "J. Smith",
    "position": "F",
    "team_id": 42,
    "team_name": "Arsenal",
    "value": 6,
    "matches": 7,
}, 
{
    "rank": 2,
    "player_id": 872,
    "player_name": "K. Kvara",
    "position": "F",
    "team_id": 13,
    "team_name": "PSG",
    "value": 5,
    "matches": 5,
},
{
    "rank": 3,
    "player_id": 924,
    "player_name": "K. Mbappe",
    "position": "F",
    "team_id": 12,
    "team_name": "Real Madrid",
    "value": 5,
    "matches": 7,
}]

RAW_STANDINGS = [{
    "position": 1,
    "team_id": 42,
    "team_name": "Arsenal",
    "played": 7,
    "won": 5,
    "drawn": 2,
    "lost": 0,
    "gf": 14,
    "ga": 4,
    "gd": 10,
    "pts": 17,
    "xgf": 13.2,
    "xga": 5.1,
    "xgd": 8.1,
    "xg_games": 7,
    "form": "WWDWW",
    "live": False,
    "zone": {
        "key": "cl",
        "label": "Champions League",
        "type": "qualification",
    },
}, {
"position": 1,
    "team_id": 13,
    "team_name": "PSG",
    "played": 7,
    "won": 5,
    "drawn": 2,
    "lost": 0,
    "gf": 14,
    "ga": 4,
    "gd": 10,
    "pts": 17,
    "xgf": 13.2,
    "xga": 5.1,
    "xgd": 8.1,
    "xg_games": 7,
    "form": "WWDWW",
    "live": False,
    "zone": {
        "key": "cl",
        "label": "Champions League",
        "type": "qualification",
    },
},
{
"position": 3,
    "team_id": 12,
    "team_name": "Real Madrid",
    "played": 7,
    "won": 5,
    "drawn": 2,
    "lost": 0,
    "gf": 14,
    "ga": 4,
    "gd": 10,
    "pts": 17,
    "xgf": 13.2,
    "xga": 5.1,
    "xgd": 8.1,
    "xg_games": 7,
    "form": "WWDWW",
    "live": False,
    "zone": {
        "key": "cl",
        "label": "Champions League",
        "type": "qualification",
    },
}
]

RAW_STAGE = {
    "stage": "regular-season",
    "stage_name": "Regular season",
    "matches": 380,
    "rounds": 38,
    "start_date": "2026-08-21",
    "end_date": "2027-05-30",
}


def test_transform_fixture():
    new_fixture = transform_fixture(RAW_FIXTURE)
    expected_keys = set(["id", "league_id", "home_team_id", "home_team", "home_coach_id",
                     "away_team_id", "away_team", "away_coach_id", "referee_id", "round_number",
                     "round_name", "group_name", "stage", "stage_name", "venue_id", "event_date",
                     "status", "home_score", "away_score", "current_minute", "home_score_ht", "away_score_ht", "last_updated"])
    assert new_fixture.keys() == expected_keys
    
def test_transform_stat():
    new_stat = transform_stat(RAW_STATS, league_id=2, curr_season=2034, stat_type="goals")
    expected_keys = set(["league_id", "season_id", "stat_type", "rank", "player_id", "player_name",
                         "player_position", "team_id", "team_name", "value", "matches"])
    assert new_stat[0].keys() == expected_keys
    assert new_stat[1].keys() == expected_keys
    assert new_stat[2].keys() == expected_keys
    
def test_transform_standings():
    new_standing = transform_standings(RAW_STANDINGS, league_id=7, curr_season=127)
    expected_keys = set(["league_id", "season_id", "team_id", "team_name", "position", "played", "won", "drawn", "lost", "gf", "ga",
                         "gd", "pts", "xgf", "xga", "xgd", "form", "zone_key", "zone_label", "zone_type"])
    assert new_standing[0].keys() == expected_keys
    assert new_standing[1].keys() == expected_keys
    assert new_standing[2].keys() == expected_keys
    
def test_raw_stage():
    new_stage = transform_stage(RAW_STAGE, league_id=7, season_id=2893, sort_order=1)
    expected_keys = set(["season_id", "league_id", "stage", "stage_name", "rounds", "sort_order", "start_date", "end_date"])

    assert new_stage.keys() == expected_keys


@pytest.mark.parametrize("raw_date", [
    "2026-10-04T15:30:00+00:00",  # events/
    "2026-10-04T15:30:00Z",       # events/live/
])
def test_fixture_event_date_parsed_as_utc(raw_date):
    new_fixture = transform_fixture({**RAW_FIXTURE, "event_date": raw_date})

    assert new_fixture["event_date"] == datetime(2026, 10, 4, 15, 30, tzinfo=timezone.utc)

def test_fixture_last_updated_stamped_when_missing():
    before = datetime.now(timezone.utc)
    new_fixture = transform_fixture(RAW_FIXTURE)
    after = datetime.now(timezone.utc)

    assert new_fixture["last_updated"].tzinfo is not None
    assert before <= new_fixture["last_updated"] <= after


def test_fixture_last_updated_parsed_when_present():
    new_fixture = transform_fixture({**RAW_FIXTURE, "last_updated": "2026-10-04T17:25:00+00:00"})

    assert new_fixture["last_updated"] == datetime(2026, 10, 4, 17, 25, tzinfo=timezone.utc)


def test_stage_dates_parsed_as_utc_midnight():
    new_stage = transform_stage(RAW_STAGE, league_id=7, season_id=2893, sort_order=1)

    assert new_stage["start_date"] == datetime(2026, 8, 21, tzinfo=timezone.utc)
    assert new_stage["end_date"] == datetime(2027, 5, 30, tzinfo=timezone.utc)
    
