import pytest
from unittest.mock import MagicMock
import pandas as pd


def make_mock_session(session_type="R"):
    session = MagicMock()
    session.event = pd.Series({
        "EventName": "Miami Grand Prix",
        "Location": "Miami",
        "RoundNumber": 6,
        "OfficialEventName": "Formula 1 Crypto.com Miami Grand Prix 2026",
    })
    session.date = pd.Timestamp("2026-05-04 20:00:00")
    session.name = "Race" if session_type == "R" else "Qualifying"

    results = pd.DataFrame({
        "DriverNumber": ["4", "44", "16"],
        "Abbreviation": ["NOR", "HAM", "LEC"],
        "FullName": ["Lando Norris", "Lewis Hamilton", "Charles Leclerc"],
        "TeamName": ["McLaren", "Ferrari", "Ferrari"],
        "Position": [1.0, 2.0, 3.0],
        "GridPosition": [1.0, 3.0, 2.0],
        "Status": ["Finished", "Finished", "Finished"],
        "Points": [25.0, 18.0, 15.0],
    })
    session.results = results
    return session


def test_parse_race_results_returns_list_of_dicts():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("R")
    rows = parse_results(session, season=2026, round_num=6)
    assert len(rows) == 3
    assert rows[0]["driver_name"] == "Lando Norris"
    assert rows[0]["position"] == 1
    assert rows[0]["season"] == 2026
    assert rows[0]["round"] == 6


def test_parse_results_includes_points():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("R")
    rows = parse_results(session, season=2026, round_num=6)
    assert rows[0]["points"] == 25.0
    assert rows[1]["points"] == 18.0


def test_parse_results_handles_missing_points_column():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("R")
    session.results = session.results.drop(columns=["Points"])
    rows = parse_results(session, season=2026, round_num=6)
    assert rows[0].get("points") is None


def test_parse_qualifying_uses_session_type_q():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("Q")
    rows = parse_results(session, season=2026, round_num=6, session_type="Q")
    assert rows[0]["session_type"] == "Q"
    assert rows[1]["grid_position"] == 3


def test_parse_results_race_name_from_event():
    from tools.ingest_fastf1 import get_race_name
    session = make_mock_session("R")
    name = get_race_name(session)
    assert name == "Miami Grand Prix"


def test_parse_results_circuit_from_location():
    from tools.ingest_fastf1 import get_circuit
    session = make_mock_session("R")
    circuit = get_circuit(session)
    assert circuit == "Miami"
