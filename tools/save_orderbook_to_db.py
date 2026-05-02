"""
Save an orderbook snapshot JSON file to the DB (orderbook_snapshots table).

Usage:
    python -m tools.save_orderbook_to_db .tmp/orderbook_snapshot_20260504_123000.json
    python -m tools.save_orderbook_to_db .tmp/orderbook_snapshot_*.json  # latest

Call this after running snapshot_orderbook.py to persist mid prices for the model.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

from rich.console import Console
from tools.db import cursor

console = Console()


def save_snapshot_file(path: Path) -> int:
    with open(path) as f:
        data = json.load(f)

    markets = data.get("markets", [])
    saved = 0

    with cursor() as cur:
        for m in markets:
            ticker = m.get("ticker", "")
            if not ticker:
                continue

            cur.execute("SELECT id FROM markets WHERE kalshi_ticker = %s", (ticker,))
            row = cur.fetchone()
            if row is None:
                continue
            market_id = row[0]

            yes_bid = _parse_price(m.get("yes_bid"))
            yes_ask = _parse_price(m.get("yes_ask"))
            no_bid = _parse_price(m.get("no_bid"))
            no_ask = _parse_price(m.get("no_ask"))
            volume = _parse_float(m.get("volume_24h"))
            snapped_at = m.get("snapped_at") or data.get("snapped_at") or datetime.now(timezone.utc).isoformat()

            cur.execute("""
                INSERT INTO orderbook_snapshots
                    (market_id, best_yes_bid, best_yes_ask, best_no_bid, best_no_ask, volume_24h, snapshot_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (market_id, yes_bid, yes_ask, no_bid, no_ask, volume, snapped_at))
            saved += 1

    return saved


def _parse_price(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Save orderbook snapshot JSON to DB")
    parser.add_argument("files", nargs="*", help="Snapshot file paths (default: latest in .tmp/)")
    args = parser.parse_args()

    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        tmp = Path(".tmp")
        snaps = sorted(tmp.glob("orderbook_snapshot_*.json"))
        if not snaps:
            console.print("[red]No snapshot files found in .tmp/[/]")
            return
        paths = [snaps[-1]]
        console.print(f"Using latest snapshot: {paths[0].name}")

    total = 0
    for p in paths:
        n = save_snapshot_file(p)
        console.print(f"[green]Saved {n} orderbook rows from {p.name}[/]")
        total += n

    console.print(f"[bold green]Total: {total} rows saved to orderbook_snapshots[/]")


if __name__ == "__main__":
    main()
