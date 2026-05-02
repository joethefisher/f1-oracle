"""
Snapshot order books for all open F1 markets (or specific tickers).

Writes snapshots to .tmp/orderbook_snapshot_{timestamp}.json
Also prints a summary table to the console.

Usage:
    python tools/snapshot_orderbook.py                         # all open v1 markets
    python tools/snapshot_orderbook.py --event KXF1RACE-MIAGP26
    python tools/snapshot_orderbook.py --ticker KXF1RACE-MIAGP26-NORRIS
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from rich.console import Console
from rich.table import Table

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"Accept": "application/json"}
TMP_DIR = Path(__file__).parent.parent / ".tmp"

F1_SERIES_V1 = [
    "KXF1RACE",
    "KXF1CONSTRUCTORS",
    "KXF1RACEPODIUM",
    "KXF1POLEPOSITION",
    "KXF1POLE",
    "KXF1RACESPRINT",
]

console = Console()


def get(path, params=None, retries=4):
    delay = 2
    for attempt in range(retries):
        resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params)
        if resp.status_code == 429:
            console.print(f"[yellow]Rate limited — waiting {delay}s...[/]")
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Failed after {retries} retries: {path}")


def get_open_markets(series_tickers):
    markets = []
    for st in series_tickers:
        data = get("/markets", {"series_ticker": st, "status": "open", "limit": 1000})
        markets.extend(data.get("markets", []))
        time.sleep(0.3)
    return markets


def get_markets_for_event(event_ticker):
    data = get("/markets", {"event_ticker": event_ticker, "status": "open", "limit": 1000})
    return data.get("markets", [])


def fetch_orderbook(ticker):
    data = get(f"/markets/{ticker}/orderbook", {"depth": 5})
    return data.get("orderbook_fp", {})


def best_bid_ask(orderbook):
    """Extract best bid/ask from orderbook. yes_dollars sorted desc = bids."""
    yes_levels = orderbook.get("yes_dollars", [])
    no_levels = orderbook.get("no_dollars", [])

    best_yes_bid = yes_levels[0][0] if yes_levels else None
    best_no_bid = no_levels[0][0] if no_levels else None

    # yes_ask = 1 - no_bid (in cents: yes_ask = 100 - no_bid_cents)
    yes_ask = None
    if best_no_bid is not None:
        try:
            yes_ask = f"{1.0 - float(best_no_bid):.4f}"
        except (ValueError, TypeError):
            pass

    return best_yes_bid, yes_ask


def snapshot_markets(markets):
    TMP_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc)
    results = []

    table = Table(title=f"Order Book Snapshot — {ts.strftime('%Y-%m-%d %H:%M UTC')}")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Yes Bid", justify="right")
    table.add_column("Yes Ask", justify="right")
    table.add_column("Spread", justify="right")
    table.add_column("Vol 24h", justify="right")

    for m in markets:
        ticker = m["ticker"]
        try:
            ob = fetch_orderbook(ticker)
            bid, ask = best_bid_ask(ob)
            time.sleep(0.2)
        except Exception as e:
            console.print(f"[red]Error fetching {ticker}: {e}[/]")
            bid, ask, ob = None, None, {}

        spread = None
        if bid and ask:
            try:
                spread = f"{float(ask) - float(bid):.4f}"
            except ValueError:
                pass

        results.append({
            "ticker": ticker,
            "title": m.get("yes_sub_title") or m.get("title", ""),
            "event_ticker": m.get("event_ticker", ""),
            "yes_bid": bid,
            "yes_ask": ask,
            "spread": spread,
            "volume_24h": m.get("volume_24h_fp"),
            "open_interest": m.get("open_interest_fp"),
            "orderbook": ob,
            "snapped_at": ts.isoformat(),
        })

        table.add_row(
            ticker[:40],
            (m.get("yes_sub_title") or m.get("title", ""))[:45],
            str(bid) if bid else "—",
            str(ask) if ask else "—",
            str(spread) if spread else "—",
            str(m.get("volume_24h_fp", "—")),
        )

    console.print(table)

    filename = TMP_DIR / f"orderbook_snapshot_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump({"snapped_at": ts.isoformat(), "markets": results}, f, indent=2)
    console.print(f"\n[green]Saved to {filename}[/]")
    return results


def main():
    parser = argparse.ArgumentParser(description="Snapshot Kalshi F1 order books")
    parser.add_argument("--event", help="Filter by event ticker (e.g. KXF1RACE-MIAGP26)")
    parser.add_argument("--ticker", help="Single market ticker")
    args = parser.parse_args()

    try:
        if args.ticker:
            data = get(f"/markets/{args.ticker}")
            markets = [data.get("market", {})]
        elif args.event:
            console.print(f"Fetching markets for event [cyan]{args.event}[/]...")
            markets = get_markets_for_event(args.event)
        else:
            console.print("Fetching all open v1 F1 markets...")
            markets = get_open_markets(F1_SERIES_V1)

        if not markets:
            console.print("[yellow]No markets found.[/]")
            sys.exit(0)

        console.print(f"Snapping order books for [bold]{len(markets)}[/] markets...\n")
        snapshot_markets(markets)

    except requests.HTTPError as e:
        console.print(f"[red]HTTP {e.response.status_code}: {e.response.text}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
