from unittest.mock import patch, MagicMock
import pytest


def _mock_response(payload: dict):
    mock = MagicMock()
    mock.json.return_value = payload
    mock.raise_for_status = MagicMock()
    return mock


RACE_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [{
                "raceName": "Bahrain Grand Prix",
                "Results": [
                    {
                        "position": "1",
                        "grid": "1",
                        "points": "25",
                        "status": "Finished",
                        "Driver": {"code": "LEC", "givenName": "Charles", "familyName": "Leclerc", "permanentNumber": "16"},
                        "Constructor": {"name": "Ferrari"},
                    },
                    {
                        "position": "2",
                        "grid": "3",
                        "points": "18",
                        "status": "Finished",
                        "Driver": {"code": "SAI", "givenName": "Carlos", "familyName": "Sainz", "permanentNumber": "55"},
                        "Constructor": {"name": "Ferrari"},
                    },
                ],
            }]
        }
    }
}

QUALI_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [{
                "raceName": "Bahrain Grand Prix",
                "QualifyingResults": [
                    {
                        "position": "1",
                        "Driver": {"code": "LEC", "givenName": "Charles", "familyName": "Leclerc", "permanentNumber": "16"},
                        "Constructor": {"name": "Ferrari"},
                    },
                    {
                        "position": "2",
                        "Driver": {"code": "SAI", "givenName": "Carlos", "familyName": "Sainz", "permanentNumber": "55"},
                        "Constructor": {"name": "Ferrari"},
                    },
                ],
            }]
        }
    }
}


def test_fetch_race_results_returns_list():
    with patch("requests.get", return_value=_mock_response(RACE_PAYLOAD)):
        from tools.jolpica import fetch_race_results
        rows = fetch_race_results(2022, 1)
    assert len(rows) == 2


def test_fetch_race_results_position():
    with patch("requests.get", return_value=_mock_response(RACE_PAYLOAD)):
        from tools.jolpica import fetch_race_results
        rows = fetch_race_results(2022, 1)
    assert rows[0]["position"] == 1
    assert rows[0]["abbreviation"] == "LEC"


def test_fetch_race_results_grid_position():
    with patch("requests.get", return_value=_mock_response(RACE_PAYLOAD)):
        from tools.jolpica import fetch_race_results
        rows = fetch_race_results(2022, 1)
    assert rows[1]["grid_position"] == 3


def test_fetch_race_results_points():
    with patch("requests.get", return_value=_mock_response(RACE_PAYLOAD)):
        from tools.jolpica import fetch_race_results
        rows = fetch_race_results(2022, 1)
    assert rows[0]["points"] == 25.0


def test_fetch_race_results_empty_when_no_races():
    empty_payload = {"MRData": {"RaceTable": {"Races": []}}}
    with patch("requests.get", return_value=_mock_response(empty_payload)):
        from tools.jolpica import fetch_race_results
        rows = fetch_race_results(2022, 99)
    assert rows == []


def test_fetch_qualifying_results_returns_list():
    with patch("requests.get", return_value=_mock_response(QUALI_PAYLOAD)):
        from tools.jolpica import fetch_qualifying_results
        rows = fetch_qualifying_results(2022, 1)
    assert len(rows) == 2


def test_fetch_qualifying_results_position():
    with patch("requests.get", return_value=_mock_response(QUALI_PAYLOAD)):
        from tools.jolpica import fetch_qualifying_results
        rows = fetch_qualifying_results(2022, 1)
    assert rows[0]["position"] == 1
    assert rows[0]["abbreviation"] == "LEC"


def test_fetch_qualifying_grid_equals_position():
    with patch("requests.get", return_value=_mock_response(QUALI_PAYLOAD)):
        from tools.jolpica import fetch_qualifying_results
        rows = fetch_qualifying_results(2022, 1)
    assert rows[0]["grid_position"] == rows[0]["position"]
