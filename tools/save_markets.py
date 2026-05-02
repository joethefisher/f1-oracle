"""
Write discovered Kalshi markets to the database.

Usage:
    python tools/save_markets.py --race-id 1 --event KXF1RACE-MIAGP26 --type race_winner
"""

import argparse
import time
import requests
from rich.console import Console

from tools.db import cursor

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"Accept": "application/json"}
console = Console()


def build_market_rows(markets: list[dict], race_id: int, market_type: str) -> list[dict]:
    rows = []
    for m in markets:
        driver_name = m.get("yes_sub_title") or m.get("title", "")
        rows.append({
            "race_id": race_id,
            "kalshi_ticker": m["ticker"],
            "kalshi_event_ticker": m["event_ticker"],
            "market_type": market_type,
            "driver_name": driver_name,
            "status": m.get("status", "open"),
        })
    return rows


def fetch_markets_for_event(event_ticker: str) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/markets",
        headers=HEADERS,
        params={"event_ticker": event_ticker, "limit": 200},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("markets", [])


def save_markets(race_id: int, event_ticker: str, market_type: str):
    markets = fetch_markets_for_event(event_ticker)
    rows = build_market_rows(markets, race_id, market_type)

    with cursor() as cur:
        for row in rows:
            cur.execute("""
                INSERT INTO markets
                    (race_id, kalshi_ticker, kalshi_event_ticker, market_type, driver_name, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (kalshi_ticker) DO UPDATE
                    SET status = EXCLUDED.status
            """, (
                row["race_id"], row["kalshi_ticker"], row["kalshi_event_ticker"],
                row["market_type"], row["driver_name"], row["status"],
            ))
    console.print(f"[green]Saved {len(rows)} {market_type} markets for {event_ticker}[/]")


def main():
    parser = argparse.ArgumentParser(description="Save Kalshi markets to DB")
    parser.add_argument("--race-id", type=int, required=True)
    parser.add_argument("--event", required=True, help="Kalshi event ticker")
    parser.add_argument(
        "--type", required=True, dest="market_type",
        choices=["race_winner", "sprint_winner", "podium", "pole", "constructors"],
    )
    args = parser.parse_args()
    save_markets(args.race_id, args.event, args.market_type)


if __name__ == "__main__":
    main()
