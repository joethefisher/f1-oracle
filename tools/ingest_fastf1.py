"""
Ingest F1 session data from FastF1 into the database.

Usage:
    python tools/ingest_fastf1.py --season 2026 --round 6 --session R
    python tools/ingest_fastf1.py --season 2026 --round 6 --session Q

Sessions: R=Race, Q=Qualifying, S=Sprint, SQ=Sprint Qualifying
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


def parse_results(session, season: int, round_num: int, session_type: str = "R") -> list[dict[str, Any]]:
    rows = []
    for _, driver in session.results.iterrows():
        row: dict[str, Any] = {
            "season": season,
            "round": round_num,
            "session_type": session_type,
            "driver_number": str(driver.get("DriverNumber", "")),
            "abbreviation": str(driver.get("Abbreviation", "")),
            "driver_name": str(driver.get("FullName", "")),
            "team_name": str(driver.get("TeamName", "")),
            "position": int(driver["Position"]) if pd.notna(driver.get("Position")) else None,
            "grid_position": int(driver["GridPosition"]) if pd.notna(driver.get("GridPosition")) else None,
            "status": str(driver.get("Status", "")),
            "points": float(driver["Points"]) if "Points" in driver.index and pd.notna(driver.get("Points")) else None,
        }
        rows.append(row)
    return rows


def load_session(season: int, round_num: int, session_type: str):
    console.print(f"Loading FastF1: season={season} round={round_num} session={session_type}")
    session = fastf1.get_session(season, round_num, session_type)
    session.load(telemetry=False, weather=False, messages=False)
    return session


def upsert_race(season: int, round_num: int, session) -> int:
    name = get_race_name(session)
    circuit = get_circuit(session)
    race_date = session.date.isoformat() if hasattr(session.date, "isoformat") else str(session.date)

    with cursor() as cur:
        cur.execute("""
            INSERT INTO races (season, round, name, circuit, race_date_utc, status)
            VALUES (%s, %s, %s, %s, %s, 'completed')
            ON CONFLICT (season, round) DO UPDATE
                SET name = EXCLUDED.name,
                    circuit = EXCLUDED.circuit,
                    race_date_utc = EXCLUDED.race_date_utc,
                    status = 'completed'
            RETURNING id
        """, (season, round_num, name, circuit, race_date))
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


def ingest(season: int, round_num: int, session_type: str = "R"):
    session = load_session(season, round_num, session_type)
    rows = parse_results(session, season, round_num, session_type)
    race_id = upsert_race(season, round_num, session)
    upsert_results(rows, race_id, session_type)
    console.print(f"[green]Ingested {season} R{round_num} ({session_type}) — {len(rows)} drivers[/]")


def main():
    parser = argparse.ArgumentParser(description="Ingest F1 session data from FastF1")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True, dest="round_num")
    parser.add_argument("--session", default="R", choices=["R", "Q", "S", "SQ"])
    args = parser.parse_args()
    ingest(args.season, args.round_num, args.session)


if __name__ == "__main__":
    main()
