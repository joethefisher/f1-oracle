"""
Centralized Kalshi public API client and orderbook parsing.

All Kalshi HTTP access and orderbook/market parsing lives here so a single API
change only needs one edit. This logic was previously copy-pasted across 5+
tools (orchestrate, snapshot_orderbook, explore_markets, save_markets,
refresh_prices); when Kalshi migrated the orderbook response from the legacy
`orderbook`/`yes` cents format to `orderbook_fp`/`yes_dollars` dollar strings,
only one copy was updated and the production path silently parsed every price to
null. One module prevents that class of drift.

No authentication required — these are all public endpoints.
"""
import logging
import time

import requests

log = logging.getLogger("kalshi")

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"Accept": "application/json"}
DEFAULT_TIMEOUT = 15


# ─────────────────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────────────────

def get(path: str, params: dict | None = None, retries: int = 4,
        timeout: int = DEFAULT_TIMEOUT) -> dict:
    """GET a Kalshi endpoint with exponential backoff on 429."""
    delay = 2
    for attempt in range(retries):
        resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS,
                            params=params or {}, timeout=timeout)
        if resp.status_code == 429:
            log.warning("Kalshi rate limited — waiting %ds (attempt %d)", delay, attempt + 1)
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Kalshi API failed after {retries} retries: {path}")


def paginate(path: str, key: str, params: dict | None = None,
             page_pause: float = 0.5) -> list:
    """Follow Kalshi cursor pagination, accumulating ``data[key]`` across pages."""
    params = dict(params or {})
    results: list = []
    cursor = None
    while True:
        if cursor:
            params["cursor"] = cursor
        data = get(path, params)
        results.extend(data.get(key, []))
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(page_pause)
    return results


def fetch_orderbook(ticker: str, depth: int = 5) -> dict:
    return get(f"/markets/{ticker}/orderbook", {"depth": depth})


def fetch_markets_for_event(event_ticker: str, limit: int = 200) -> list:
    return paginate("/markets", "markets", {"event_ticker": event_ticker, "limit": limit})


def fetch_events(series_ticker: str, status: str = "open", limit: int = 200) -> list:
    return paginate("/events", "events", {
        "series_ticker": series_ticker,
        "status": status,
        "with_nested_markets": "false",
        "limit": limit,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Orderbook parsing
# ─────────────────────────────────────────────────────────────────────────────

def best_price(levels: list | None) -> float | None:
    """Best (highest) resting bid price from a list of [price, size] levels.

    Kalshi's `orderbook_fp` returns prices as dollar strings (e.g. "0.3100").
    Taking the max is robust to whether levels are sorted ascending or descending.
    """
    prices = []
    for level in levels or []:
        try:
            prices.append(float(level[0]))
        except (ValueError, TypeError, IndexError):
            continue
    return max(prices) if prices else None


def parse_orderbook(data: dict):
    """Extract (yes_bid, yes_ask, no_bid, no_ask) from a Kalshi orderbook response.

    The current API returns `orderbook_fp` with `yes_dollars`/`no_dollars` (dollar
    strings). `yes_dollars` are resting YES bids; `no_dollars` are resting NO bids.
    The YES ask is the complement of the best NO bid (and vice versa). An empty
    side yields None for the prices derived from it. Falls back to the legacy
    `orderbook`/`yes`/`no` keys if present.
    """
    ob = data.get("orderbook_fp") or data.get("orderbook") or {}
    yes_bid = best_price(ob.get("yes_dollars") or ob.get("yes"))
    no_bid = best_price(ob.get("no_dollars") or ob.get("no"))
    yes_ask = (1.0 - no_bid) if no_bid is not None else None
    no_ask = (1.0 - yes_bid) if yes_bid is not None else None
    return yes_bid, yes_ask, no_bid, no_ask


def compute_mid(yes_bid, yes_ask) -> float | None:
    """Mid price from yes bid/ask, tolerating a missing side."""
    bid = float(yes_bid) if yes_bid is not None else None
    ask = float(yes_ask) if yes_ask is not None else None
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    return ask if ask is not None else bid
