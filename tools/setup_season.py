"""
Set up all races for a season in the DB using Jolpica schedule data.

Usage:
    python -m tools.setup_season --season 2025
"""
import argparse
import requests
import time
from rich.console import Console
from tools.db import cursor
from tools.ingest_historical import SPRINT_ROUNDS

console = Console()

BASE = "https://api.jolpi.ca/ergast/f1"


def fetch_season_schedule(season: int) -> list[dict]:
    resp = requests.get(f"{BASE}/{season}.json?limit=30", timeout=15)
    resp.raise_for_status()
    return resp.json()["MRData"]["RaceTable"]["Races"]


def setup_season(season: int):
    console.print(f"Fetching {season} schedule from Jolpica...")
    races = fetch_season_schedule(season)

    if not races:
        console.print(f"[red]No races found for {season}[/]")
        return

    console.print(f"Found {len(races)} races")
    inserted = 0
    updated = 0

    with cursor() as cur:
        for r in races:
            round_num = int(r["round"])
            name = r["raceName"]
            circuit = r["Circuit"]["Location"]["locality"]
            race_date = r["date"] + "T" + r.get("time", "14:00:00")
            is_sprint = (season, round_num) in SPRINT_ROUNDS

            cur.execute("""
                INSERT INTO races
                    (season, round, name, circuit, race_date_utc, is_sprint_weekend, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'upcoming')
                ON CONFLICT (season, round) DO UPDATE
                    SET name = EXCLUDED.name,
                        circuit = EXCLUDED.circuit,
                        race_date_utc = COALESCE(EXCLUDED.race_date_utc, races.race_date_utc),
                        is_sprint_weekend = EXCLUDED.is_sprint_weekend
                RETURNING (xmax = 0) AS inserted
            """, (season, round_num, name, circuit, race_date, is_sprint))
            was_inserted = cur.fetchone()[0]
            if was_inserted:
                inserted += 1
            else:
                updated += 1

    console.print(f"[green]Season {season}: {inserted} inserted, {updated} updated[/]")
    console.print("Use [cyan]python -m tools.check_status[/] to verify.")


def main():
    parser = argparse.ArgumentParser(description="Set up all races for a season in the DB")
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    setup_season(args.season)


if __name__ == "__main__":
    main()
