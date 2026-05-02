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
        "Position": [float("nan"), float("nan"), float("nan")],
        "GridPosition": [float("nan"), float("nan"), float("nan")],
        "ClassifiedPosition": ["", "", ""],
        "Status": ["Finished", "Finished", "Finished"],
        "Points": [25.0, 18.0, 15.0],
    })
    session.results = results

    # Build mock laps — 3 drivers × 5 laps
    lap_rows = []
    grid = {"NOR": 1, "HAM": 3, "LEC": 2}
    finish = {"NOR": 1, "HAM": 2, "LEC": 3}
    import datetime
    base = datetime.timedelta(minutes=1, seconds=30)
    for drv in ["NOR", "HAM", "LEC"]:
        for lap in range(1, 6):
            pos = grid[drv] if lap == 1 else finish[drv]
            lap_rows.append({
                "Driver": drv,
                "LapNumber": lap,
                "Position": float(pos),
                "LapTime": base + datetime.timedelta(seconds=(finish[drv] - 1) * 0.5),
            })
    session.laps = pd.DataFrame(lap_rows)
    return session


def test_parse_race_results_returns_list_of_dicts():
    from tools.ingest_fastf1 import parse_results_race
    session = make_mock_session("R")
    rows = parse_results_race(session, season=2026, round_num=6)
    assert len(rows) == 3
    assert any(r["driver_name"] == "Lando Norris" for r in rows)


def test_parse_race_results_finish_position():
    from tools.ingest_fastf1 import parse_results_race
    session = make_mock_session("R")
    rows = parse_results_race(session, season=2026, round_num=6)
    by_abbrev = {r["abbreviation"]: r for r in rows}
    assert by_abbrev["NOR"]["position"] == 1
    assert by_abbrev["HAM"]["position"] == 2
    assert by_abbrev["LEC"]["position"] == 3


def test_parse_race_results_grid_position():
    from tools.ingest_fastf1 import parse_results_race
    session = make_mock_session("R")
    rows = parse_results_race(session, season=2026, round_num=6)
    by_abbrev = {r["abbreviation"]: r for r in rows}
    assert by_abbrev["NOR"]["grid_position"] == 1
    assert by_abbrev["HAM"]["grid_position"] == 3
    assert by_abbrev["LEC"]["grid_position"] == 2


def test_parse_race_results_includes_points():
    from tools.ingest_fastf1 import parse_results_race
    session = make_mock_session("R")
    rows = parse_results_race(session, season=2026, round_num=6)
    by_abbrev = {r["abbreviation"]: r for r in rows}
    assert by_abbrev["NOR"]["points"] == 25.0


def test_parse_race_results_season_round():
    from tools.ingest_fastf1 import parse_results_race
    session = make_mock_session("R")
    rows = parse_results_race(session, season=2026, round_num=6)
    assert all(r["season"] == 2026 for r in rows)
    assert all(r["round"] == 6 for r in rows)


def test_parse_qualifying_returns_list():
    from tools.ingest_fastf1 import parse_results_qualifying
    session = make_mock_session("Q")
    rows = parse_results_qualifying(session, season=2026, round_num=6)
    assert len(rows) == 3


def test_parse_qualifying_position_by_best_lap():
    from tools.ingest_fastf1 import parse_results_qualifying
    session = make_mock_session("Q")
    rows = parse_results_qualifying(session, season=2026, round_num=6)
    by_abbrev = {r["abbreviation"]: r for r in rows}
    # NOR has fastest lap in mock (finish pos 1 = shortest LapTime offset)
    assert by_abbrev["NOR"]["position"] == 1


def test_parse_qualifying_session_type_marker():
    from tools.ingest_fastf1 import parse_results_qualifying
    session = make_mock_session("Q")
    rows = parse_results_qualifying(session, season=2026, round_num=6)
    assert all(r["session_type"] == "Q" for r in rows)


def test_get_race_name_from_event():
    from tools.ingest_fastf1 import get_race_name
    session = make_mock_session("R")
    name = get_race_name(session)
    assert name == "Miami Grand Prix"


def test_get_circuit_from_location():
    from tools.ingest_fastf1 import get_circuit
    session = make_mock_session("R")
    circuit = get_circuit(session)
    assert circuit == "Miami"
