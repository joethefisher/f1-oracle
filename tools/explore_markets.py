"""
Discover F1 markets on Kalshi using public endpoints (no auth required).

Usage:
    python tools/explore_markets.py                  # list F1 series + events
    python tools/explore_markets.py --markets        # list open F1 markets
    python tools/explore_markets.py --markets --all  # include closed/settled
"""

import argparse
import sys
import time
import requests
from rich.console import Console
from rich.table import Table

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"Accept": "application/json"}

# Series in scope for v1 (race winner, constructors, podium, pole, sprint)
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
    """GET with exponential backoff on 429."""
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


def paginate(path, key, params=None):
    params = params or {}
    results = []
    cursor = None
    while True:
        if cursor:
            params["cursor"] = cursor
        data = get(path, params)
        results.extend(data.get(key, []))
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.5)  # 500ms between pages
    return results


def list_f1_series():
    """Show all F1-related series discovered on Kalshi."""
    console.rule("[bold]F1 Series on Kalshi")
    data = get("/series")
    series_list = data.get("series", [])
    f1 = [s for s in series_list
          if "f1" in s.get("ticker", "").lower()
          or "formula" in str(s.get("title", "")).lower()]

    table = Table(title=f"F1 Series ({len(f1)} found)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Title")
    table.add_column("In v1 scope", style="green")
    for s in f1:
        in_scope = "✓" if s["ticker"] in F1_SERIES_V1 else ""
        table.add_row(s.get("ticker", ""), s.get("title", ""), in_scope)
    console.print(table)


def list_events():
    console.rule("[bold]Open F1 Events (v1 series only)")
    all_events = []
    for st in F1_SERIES_V1:
        console.print(f"  Fetching events for [cyan]{st}[/]...")
        events = paginate("/events", "events", {
            "series_ticker": st,
            "status": "open",
            "with_nested_markets": "false",
            "limit": 200,
        })
        all_events.extend(events)
        time.sleep(0.5)

    if not all_events:
        console.print("[yellow]No open events found for v1 series.[/]")
        return []

    table = Table(title=f"Open F1 Events ({len(all_events)})")
    table.add_column("Event Ticker", style="cyan")
    table.add_column("Series")
    table.add_column("Title")
    for e in all_events:
        table.add_row(
            e.get("event_ticker", ""),
            e.get("series_ticker", ""),
            e.get("title", ""),
        )
    console.print(table)
    return [e["event_ticker"] for e in all_events]


def list_markets(include_all=False):
    console.rule("[bold]F1 Markets (v1 series only)")
    all_markets = []
    for st in F1_SERIES_V1:
        console.print(f"  Fetching markets for [cyan]{st}[/]...")
        params = {"series_ticker": st, "limit": 1000}
        if not include_all:
            params["status"] = "open"
        markets = paginate("/markets", "markets", params)
        all_markets.extend(markets)
        time.sleep(0.5)

    if not all_markets:
        console.print("[yellow]No markets found.[/]")
        return

    table = Table(title=f"F1 Markets ({len(all_markets)})")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Yes Bid", justify="right")
    table.add_column("Yes Ask", justify="right")
    table.add_column("Vol 24h", justify="right")
    for m in all_markets:
        title = m.get("yes_sub_title") or m.get("title", "")
        table.add_row(
            m.get("ticker", ""),
            title[:60],
            m.get("status", ""),
            m.get("yes_bid_dollars", "—"),
            m.get("yes_ask_dollars", "—"),
            m.get("volume_24h_fp", "—"),
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Explore Kalshi F1 markets")
    parser.add_argument("--markets", action="store_true", help="List markets instead of events")
    parser.add_argument("--all", action="store_true", help="Include non-open markets")
    args = parser.parse_args()

    try:
        list_f1_series()

        if args.markets:
            list_markets(include_all=args.all)
        else:
            list_events()

    except requests.HTTPError as e:
        console.print(f"[red]HTTP {e.response.status_code}: {e.response.text}[/]")
        sys.exit(1)
    except requests.ConnectionError:
        console.print("[red]Connection error — check your internet.[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
