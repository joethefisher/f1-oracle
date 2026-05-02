"""
Bulk ingest FastF1 historical data for multiple seasons.

Usage:
    python tools/ingest_historical.py --seasons 2022 2023 2024
    python tools/ingest_historical.py --seasons 2022 2023 2024 --session Q
"""
import argparse
import time
from rich.console import Console

from tools.ingest_fastf1 import ingest

console = Console()

SEASON_ROUNDS = {2022: 22, 2023: 22, 2024: 24, 2025: 24}

SPRINT_ROUNDS = {
    (2022, 4), (2022, 11), (2022, 21),
    (2023, 4), (2023, 6), (2023, 12), (2023, 18), (2023, 20), (2023, 22),
    (2024, 5), (2024, 6), (2024, 11), (2024, 20), (2024, 21), (2024, 22),
    (2025, 1), (2025, 11), (2025, 14), (2025, 20), (2025, 21), (2025, 23),
}


def get_rounds_for_season(season: int) -> list[dict]:
    total = SEASON_ROUNDS.get(season, 24)
    return [
        {"round_num": r, "has_sprint": (season, r) in SPRINT_ROUNDS}
        for r in range(1, total + 1)
    ]


def ingest_season(season: int, session_type: str = "R", delay: float = 1.0):
    for entry in get_rounds_for_season(season):
        r = entry["round_num"]
        try:
            ingest(season, r, session_type)
            console.print(f"[green]✓ {season} R{r} ({session_type})[/]")
        except Exception as e:
            console.print(f"[yellow]✗ {season} R{r} ({session_type}): {e}[/]")
        time.sleep(delay)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", default=[2022, 2023, 2024])
    parser.add_argument("--session", default="R", choices=["R", "Q", "S"])
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    for season in args.seasons:
        ingest_season(season, args.session, args.delay)


if __name__ == "__main__":
    main()
