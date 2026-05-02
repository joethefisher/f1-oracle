"""
Create or update a race entry in the DB for an upcoming race weekend.

Usage:
    python -m tools.setup_race --season 2025 --round 8

This is the first step of the race weekend workflow — run it before save_markets.
"""
import argparse
from rich.console import Console
from tools.db import cursor

console = Console()


def _fetch_from_jolpica(season: int, round_num: int) -> dict | None:
    """Fetch race schedule info from Jolpica for upcoming races."""
    import requests
    try:
        resp = requests.get(
            f"https://api.jolpi.ca/ergast/f1/{season}/{round_num}.json",
            timeout=10,
        )
        resp.raise_for_status()
        races = resp.json()["MRData"]["RaceTable"]["Races"]
        if not races:
            return None
        r = races[0]
        return {
            "name": r["raceName"],
            "circuit": r["Circuit"]["Location"]["locality"],
            "race_date_utc": r["date"] + "T" + r.get("time", "14:00:00"),
        }
    except Exception as e:
        console.print(f"[yellow]Jolpica fetch failed: {e}[/]")
        return None


def setup_race(season: int, round_num: int, is_sprint: bool = False) -> int:
    """Create or update the race row in DB. Returns race_id."""
    info = _fetch_from_jolpica(season, round_num)

    if info:
        name = info["name"]
        circuit = info["circuit"]
        race_date = info["race_date_utc"]
    else:
        name = f"{season} Round {round_num}"
        circuit = "Unknown"
        race_date = None

    with cursor() as cur:
        cur.execute("""
            INSERT INTO races
                (season, round, name, circuit, race_date_utc, is_sprint_weekend, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'upcoming')
            ON CONFLICT (season, round) DO UPDATE
                SET name = EXCLUDED.name,
                    circuit = EXCLUDED.circuit,
                    race_date_utc = COALESCE(EXCLUDED.race_date_utc, races.race_date_utc),
                    is_sprint_weekend = EXCLUDED.is_sprint_weekend
            RETURNING id
        """, (season, round_num, name, circuit, race_date, is_sprint))
        race_id = cur.fetchone()[0]

    console.print(f"[green]Race set up: {name} ({circuit}) — id={race_id}[/]")
    return race_id


def main():
    parser = argparse.ArgumentParser(description="Create/update a race entry in the DB")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True, dest="round_num")
    parser.add_argument("--sprint", action="store_true", help="Mark as sprint weekend")
    args = parser.parse_args()
    setup_race(args.season, args.round_num, is_sprint=args.sprint)


if __name__ == "__main__":
    main()
