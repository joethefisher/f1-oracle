"""
Ingest F1 session data from FastF1 into the database.

Usage:
    python -m tools.ingest_fastf1 --season 2026 --round 6 --session R
    python -m tools.ingest_fastf1 --season 2026 --round 6 --session Q

Sessions: R=Race, Q=Qualifying, S=Sprint
"""

import argparse
from pathlib import Path
from typing import Any

import fastf1
import pandas as pd
from rich.console import Console

from tools.db import cursor

console = Console()

CACHE_DIR = Path(__file__).parent.parent / ".tmp" / "fastf1_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))


def get_race_name(session) -> str:
    return str(session.event.get("EventName", f"Round {session.event.get('RoundNumber', '?')}"))


def get_circuit(session) -> str:
    return str(session.event.get("Location", "Unknown"))


def _build_driver_info(session) -> dict:
    """Build {abbreviation: {driver_number, full_name, team_name}} from session.results."""
    info = {}
    for _, row in session.results.iterrows():
        abbrev = str(row.get("Abbreviation", ""))
        if abbrev:
            info[abbrev] = {
                "driver_number": str(row.get("DriverNumber", "")),
                "full_name": str(row.get("FullName", "")),
                "team_name": str(row.get("TeamName", "")),
                "status": str(row.get("Status", "")),
                "points": float(row["Points"]) if "Points" in row.index and pd.notna(row.get("Points")) else None,
            }
    return info


def parse_results_race(session, season: int, round_num: int) -> list[dict[str, Any]]:
    """Extract race results using lap data for positions (Ergast fallback is unavailable)."""
    laps = session.laps
    driver_info = _build_driver_info(session)

    # Grid: position at first lap; Finish: position at last lap
    first_laps = (
        laps[laps["LapNumber"] == 1][["Driver", "Position"]]
        .rename(columns={"Position": "GridPosition"})
        .drop_duplicates("Driver")
        .set_index("Driver")
    )
    last_laps = (
        laps.sort_values("LapNumber", ascending=False)
        .drop_duplicates("Driver")[["Driver", "Position"]]
        .rename(columns={"Position": "FinishPosition"})
        .set_index("Driver")
    )

    combined = first_laps.join(last_laps, how="outer")

    rows = []
    for abbrev, d in driver_info.items():
        grid = combined.loc[abbrev, "GridPosition"] if abbrev in combined.index else None
        finish = combined.loc[abbrev, "FinishPosition"] if abbrev in combined.index else None
        rows.append({
            "season": season,
            "round": round_num,
            "session_type": "R",
            "driver_number": d["driver_number"],
            "abbreviation": abbrev,
            "driver_name": d["full_name"],
            "team_name": d["team_name"],
            "position": int(finish) if pd.notna(finish) else None,
            "grid_position": int(grid) if pd.notna(grid) else None,
            "status": d["status"],
            "points": d["points"],
        })
    return rows


def parse_results_qualifying(session, season: int, round_num: int) -> list[dict[str, Any]]:
    """Extract qualifying results using best lap time ranking."""
    laps = session.laps
    driver_info = _build_driver_info(session)

    best_times = (
        laps.groupby("Driver")["LapTime"]
        .min()
        .dropna()
        .sort_values()
        .reset_index()
    )
    best_times["quali_position"] = range(1, len(best_times) + 1)
    position_map = dict(zip(best_times["Driver"], best_times["quali_position"]))

    rows = []
    for abbrev, d in driver_info.items():
        pos = position_map.get(abbrev)
        rows.append({
            "season": season,
            "round": round_num,
            "session_type": "Q",
            "driver_number": d["driver_number"],
            "abbreviation": abbrev,
            "driver_name": d["full_name"],
            "team_name": d["team_name"],
            "position": pos,
            "grid_position": pos,
            "status": d["status"],
            "points": d["points"],
        })
    return rows


def load_session(season: int, round_num: int, session_type: str):
    console.print(f"Loading FastF1: season={season} round={round_num} session={session_type}")
    session = fastf1.get_session(season, round_num, session_type)
    session.load(telemetry=False, weather=False, messages=False, laps=True)
    return session


def upsert_race(season: int, round_num: int, session, session_type: str = "R",
                has_results: bool = True) -> int:
    name = get_race_name(session)
    circuit = get_circuit(session)
    race_date = session.date.isoformat() if hasattr(session.date, "isoformat") else str(session.date)
    # Only mark completed when ingesting the race session itself AND it returned
    # finishing positions. A future/in-progress race can load an empty R session
    # (FastF1/Jolpica return no rows) — marking it 'completed' there wrongly hides
    # the race from the orchestrator and the GitHub Actions gate. Treat that as
    # 'active' (weekend in progress) instead.
    if session_type == "R":
        new_status = "completed" if has_results else "active"
    else:
        new_status = "active"

    with cursor() as cur:
        cur.execute("""
            INSERT INTO races (season, round, name, circuit, race_date_utc, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (season, round) DO UPDATE
                SET name = EXCLUDED.name,
                    circuit = EXCLUDED.circuit,
                    race_date_utc = EXCLUDED.race_date_utc,
                    status = CASE
                        WHEN races.status = 'completed' THEN 'completed'
                        ELSE EXCLUDED.status
                    END
            RETURNING id
        """, (season, round_num, name, circuit, race_date, new_status))
        race_id = cur.fetchone()[0]
    return race_id


def upsert_results(rows: list[dict], race_id: int, session_type: str):
    table = "race_results" if session_type == "R" else "qualifying_results"
    with cursor() as cur:
        for row in rows:
            cur.execute(f"""
                INSERT INTO {table}
                    (race_id, driver_number, abbreviation, driver_name, team_name,
                     position, grid_position, status, points)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (race_id, driver_number) DO UPDATE
                    SET position      = EXCLUDED.position,
                        grid_position = EXCLUDED.grid_position,
                        status        = EXCLUDED.status,
                        points        = EXCLUDED.points
            """, (
                race_id, row["driver_number"], row["abbreviation"], row["driver_name"],
                row["team_name"], row["position"], row["grid_position"],
                row["status"], row["points"],
            ))
    console.print(f"[green]Upserted {len(rows)} rows into {table}[/]")


def _laps_available(session) -> bool:
    try:
        _ = session.laps
        return True
    except Exception:
        return False


def ingest(season: int, round_num: int, session_type: str = "R"):
    from tools.jolpica import fetch_race_results, fetch_qualifying_results

    session = load_session(season, round_num, session_type)

    if session_type == "R":
        if _laps_available(session):
            rows = parse_results_race(session, season, round_num)
        else:
            console.print(f"[yellow]Lap data unavailable, falling back to Jolpica[/]")
            jolpica_rows = fetch_race_results(season, round_num)
            rows = [
                {**r, "season": season, "round": round_num, "session_type": "R"}
                for r in jolpica_rows
            ]
    elif session_type in ("Q", "SQ"):
        if _laps_available(session):
            rows = parse_results_qualifying(session, season, round_num)
        else:
            console.print(f"[yellow]Lap data unavailable, falling back to Jolpica[/]")
            jolpica_rows = fetch_qualifying_results(season, round_num)
            rows = [
                {**r, "season": season, "round": round_num, "session_type": "Q"}
                for r in jolpica_rows
            ]
    else:
        rows = parse_results_race(session, season, round_num)

    n_with_pos = sum(1 for r in rows if r["position"] is not None)
    race_id = upsert_race(season, round_num, session, session_type, has_results=n_with_pos > 0)
    upsert_results(rows, race_id, session_type)
    console.print(f"[green]Ingested {season} R{round_num} ({session_type}) — {len(rows)} drivers, {n_with_pos} with position[/]")


def main():
    parser = argparse.ArgumentParser(description="Ingest F1 session data from FastF1")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True, dest="round_num")
    parser.add_argument("--session", default="R", choices=["R", "Q", "S", "SQ"])
    args = parser.parse_args()
    ingest(args.season, args.round_num, args.session)


if __name__ == "__main__":
    main()
