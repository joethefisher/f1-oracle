"""
F1 Oracle Pipeline Orchestrator

Runs every 30 minutes via GitHub Actions. Determines the current race weekend
phase from DB state (not wall-clock) and executes only the steps that haven't
been done yet. All steps are idempotent — safe to run multiple times.

Usage:
    python -m tools.orchestrate
    python -m tools.orchestrate --dry-run   # log only, no DB writes
    python -m tools.orchestrate --race-id 259
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("orchestrate")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Kalshi series → market_type mapping
SERIES_MARKET_TYPES: dict[str, str] = {
    "KXF1RACE":        "race_winner",
    "KXF1RACEPODIUM":  "podium",
    "KXF1POLEPOSITION": "pole",
    "KXF1POLE":        "pole",
    "KXF1RACESPRINT":  "sprint",
}

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"Accept": "application/json"}

ALL_MARKET_TYPES = ["race_winner", "podium", "pole"]


# ─────────────────────────────────────────────────────────────────────────────
# Kalshi API helpers (reused from explore_markets.py)
# ─────────────────────────────────────────────────────────────────────────────

def kalshi_get(path: str, params: dict | None = None, retries: int = 4) -> dict:
    delay = 2
    for attempt in range(retries):
        resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params or {}, timeout=15)
        if resp.status_code == 429:
            log.warning("Kalshi rate limited — waiting %ds (attempt %d)", delay, attempt + 1)
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Kalshi API failed after {retries} retries: {path}")


def kalshi_paginate(path: str, key: str, params: dict | None = None) -> list:
    params = dict(params or {})
    results: list = []
    cursor = None
    while True:
        if cursor:
            params["cursor"] = cursor
        data = kalshi_get(path, params)
        results.extend(data.get(key, []))
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.5)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# DB guard functions
# ─────────────────────────────────────────────────────────────────────────────

def _count(query: str, params: tuple) -> int:
    from tools.db import cursor
    with cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()[0]


def markets_exist_for_race(race_id: int) -> bool:
    return _count("SELECT COUNT(*) FROM markets WHERE race_id = %s", (race_id,)) > 0


def qualifying_results_exist(race_id: int) -> bool:
    return _count(
        "SELECT COUNT(*) FROM qualifying_results WHERE race_id = %s AND position IS NOT NULL",
        (race_id,),
    ) > 0


def predictions_exist(race_id: int) -> bool:
    from tools.db import cursor
    from tools.train_model import MODEL_VERSION
    with cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM predictions p
            JOIN markets m ON p.market_id = m.id
            WHERE m.race_id = %s AND p.model_version = %s
        """, (race_id, MODEL_VERSION))
        return cur.fetchone()[0] > 0


def race_results_exist(race_id: int) -> bool:
    return _count(
        "SELECT COUNT(*) FROM race_results WHERE race_id = %s AND position IS NOT NULL",
        (race_id,),
    ) > 0


def outcomes_settled(race_id: int) -> bool:
    n_markets = _count(
        "SELECT COUNT(*) FROM markets WHERE race_id = %s AND status IN ('open', 'active', 'closed')",
        (race_id,),
    )
    if n_markets == 0:
        return False
    n_outcomes = _count(
        """SELECT COUNT(*) FROM outcomes o
           JOIN markets m ON o.market_id = m.id
           WHERE m.race_id = %s""",
        (race_id,),
    )
    return n_outcomes >= n_markets


def portfolio_snapshot_exists(race_id: int) -> bool:
    return _count(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE race_id = %s",
        (race_id,),
    ) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Race discovery
# ─────────────────────────────────────────────────────────────────────────────

def find_target_race(race_id: int | None = None) -> dict | None:
    """Return the nearest active/upcoming race within 7 days, or a specific race by ID."""
    from tools.db import cursor
    with cursor() as cur:
        if race_id:
            cur.execute(
                "SELECT id, season, round, name, circuit, race_date_utc, is_sprint_weekend, status "
                "FROM races WHERE id = %s",
                (race_id,),
            )
        else:
            cur.execute(
                """SELECT id, season, round, name, circuit, race_date_utc, is_sprint_weekend, status
                   FROM races
                   WHERE status IN ('upcoming', 'active')
                     AND race_date_utc >= NOW() - INTERVAL '3 days'
                   ORDER BY race_date_utc ASC
                   LIMIT 1""",
            )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0], "season": row[1], "round": row[2], "name": row[3],
        "circuit": row[4], "race_date_utc": row[5],
        "is_sprint_weekend": row[6], "status": row[7],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Time window helpers
# ─────────────────────────────────────────────────────────────────────────────

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def in_market_discovery_window(race: dict) -> bool:
    """Markets typically open 7 days before the race."""
    race_dt = race["race_date_utc"]
    if not race_dt.tzinfo:
        race_dt = race_dt.replace(tzinfo=timezone.utc)
    return now_utc() >= race_dt - timedelta(days=8)


def in_qualifying_window(race: dict) -> bool:
    """Qualifying is ~26 hours before race. Try ingesting from T-28h to T-1h."""
    race_dt = race["race_date_utc"]
    if not race_dt.tzinfo:
        race_dt = race_dt.replace(tzinfo=timezone.utc)
    return race_dt - timedelta(hours=28) <= now_utc() <= race_dt - timedelta(hours=1)


def in_race_result_window(race: dict) -> bool:
    """Race finishes ~2h after start; try from T+1.5h to T+10h."""
    race_dt = race["race_date_utc"]
    if not race_dt.tzinfo:
        race_dt = race_dt.replace(tzinfo=timezone.utc)
    return race_dt + timedelta(hours=1, minutes=30) <= now_utc() <= race_dt + timedelta(hours=10)


def in_sprint_window(race: dict) -> bool:
    """Sprint race is Saturday — roughly T-24h to T-4h."""
    race_dt = race["race_date_utc"]
    if not race_dt.tzinfo:
        race_dt = race_dt.replace(tzinfo=timezone.utc)
    return race_dt - timedelta(hours=26) <= now_utc() <= race_dt - timedelta(hours=4)


# ─────────────────────────────────────────────────────────────────────────────
# Market discovery
# ─────────────────────────────────────────────────────────────────────────────

def _race_keywords(race_name: str) -> list[str]:
    """Extract matchable keywords from a race name, e.g. 'Miami Grand Prix' → ['miami']."""
    stopwords = {"grand", "prix", "formula", "one", "f1", "race", "winner", "podium", "pole",
                 "sprint", "position", "2024", "2025", "2026", "gp"}
    words = race_name.lower().replace("-", " ").split()
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords or [race_name.lower().split()[0]]


def find_kalshi_event_ticker(race_name: str, race_date_utc, series_ticker: str) -> str | None:
    """Find the Kalshi event ticker for a race by fuzzy-matching name + date proximity."""
    if hasattr(race_date_utc, "tzinfo") and not race_date_utc.tzinfo:
        race_date_utc = race_date_utc.replace(tzinfo=timezone.utc)

    try:
        events = kalshi_paginate("/events", "events", {
            "series_ticker": series_ticker,
            "status": "open",
            "with_nested_markets": "false",
            "limit": 200,
        })
    except Exception as e:
        log.warning("Could not fetch events for series %s: %s", series_ticker, e)
        return None

    keywords = _race_keywords(race_name)
    candidates = []
    for event in events:
        title = event.get("title", "").lower()
        if any(kw in title for kw in keywords):
            candidates.append(event)

    if not candidates:
        # Fallback: temporal proximity only (within ±4 days of race)
        for event in events:
            close_str = event.get("close_time") or event.get("end_date_iso") or ""
            if not close_str:
                continue
            try:
                close_dt = datetime.fromisoformat(close_str.rstrip("Z")).replace(tzinfo=timezone.utc)
                if abs((close_dt - race_date_utc).days) <= 4:
                    candidates.append(event)
            except ValueError:
                continue

    if not candidates:
        return None

    # Sort by temporal proximity to race_date_utc
    def proximity(event):
        close_str = event.get("close_time") or event.get("end_date_iso") or ""
        try:
            close_dt = datetime.fromisoformat(close_str.rstrip("Z")).replace(tzinfo=timezone.utc)
            return abs((close_dt - race_date_utc).total_seconds())
        except ValueError:
            return float("inf")

    best = min(candidates, key=proximity)
    return best.get("event_ticker")


def discover_and_save_markets(race: dict) -> int:
    """Auto-discover Kalshi event tickers for all series and save markets to DB."""
    race_id = race["id"]
    race_name = race["name"]
    race_date = race["race_date_utc"]
    is_sprint = race["is_sprint_weekend"]

    series_to_check = list(SERIES_MARKET_TYPES.items())
    if not is_sprint:
        series_to_check = [(s, m) for s, m in series_to_check if m != "sprint"]

    # Deduplicate: if two series map to the same market_type, use whichever finds a ticker first
    seen_market_types: set[str] = set()
    total_saved = 0

    for series_ticker, market_type in series_to_check:
        if market_type in seen_market_types:
            continue
        log.info("Discovering %s markets for %s (series: %s)", market_type, race_name, series_ticker)
        if DRY_RUN:
            log.info("[DRY RUN] Would search %s", series_ticker)
            continue
        event_ticker = find_kalshi_event_ticker(race_name, race_date, series_ticker)
        if not event_ticker:
            log.info("No Kalshi event found yet for %s (%s) — will retry", market_type, series_ticker)
            continue
        log.info("Found event ticker: %s → saving %s markets", event_ticker, market_type)
        try:
            from tools.save_markets import save_markets
            n = save_markets(race_id, event_ticker, market_type) or 0
            total_saved += n
            seen_market_types.add(market_type)
        except Exception as e:
            log.error("Failed to save %s markets: %s", market_type, e)
        time.sleep(0.5)

    return total_saved


# ─────────────────────────────────────────────────────────────────────────────
# Orderbook snapshot + price refresh
# ─────────────────────────────────────────────────────────────────────────────

def _best_price(levels: list) -> float | None:
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


def _parse_orderbook(data: dict):
    """Extract (yes_bid, yes_ask, no_bid, no_ask) from a Kalshi orderbook response.

    The current API returns `orderbook_fp` with `yes_dollars`/`no_dollars` (dollar
    strings). `yes_dollars` are resting YES bids; `no_dollars` are resting NO bids.
    The YES ask is the complement of the best NO bid (and vice versa). An empty
    side yields None for the prices derived from it.
    """
    ob = data.get("orderbook_fp") or data.get("orderbook") or {}
    yes_bid = _best_price(ob.get("yes_dollars") or ob.get("yes"))
    no_bid  = _best_price(ob.get("no_dollars") or ob.get("no"))
    yes_ask = (1.0 - no_bid) if no_bid is not None else None
    no_ask  = (1.0 - yes_bid) if yes_bid is not None else None
    return yes_bid, yes_ask, no_bid, no_ask


def _compute_mid(yes_bid, yes_ask) -> float | None:
    bid = float(yes_bid) if yes_bid is not None else None
    ask = float(yes_ask) if yes_ask is not None else None
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    return ask or bid


def snapshot_and_persist_orderbook(race_id: int) -> int:
    """Fetch current orderbook for all open markets for this race and write to DB."""
    from tools.db import cursor

    with cursor() as cur:
        cur.execute(
            "SELECT id, kalshi_ticker FROM markets WHERE race_id = %s AND status IN ('open', 'active')",
            (race_id,),
        )
        markets = cur.fetchall()

    if not markets:
        return 0

    saved = 0
    for market_id, ticker in markets:
        try:
            data = kalshi_get(f"/markets/{ticker}/orderbook", {"depth": 5})
            best_yes_bid, best_yes_ask, best_no_bid, best_no_ask = _parse_orderbook(data)
            volume_24h    = data.get("market", {}).get("volume_24h_fp")

            if DRY_RUN:
                log.info("[DRY RUN] Would snapshot %s: yes_bid=%s yes_ask=%s", ticker, best_yes_bid, best_yes_ask)
                saved += 1
                continue

            with cursor() as cur:
                cur.execute("""
                    INSERT INTO orderbook_snapshots
                        (market_id, best_yes_bid, best_yes_ask, best_no_bid, best_no_ask, volume_24h, snapshot_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (market_id, best_yes_bid, best_yes_ask, best_no_bid, best_no_ask, volume_24h))
            saved += 1
            time.sleep(0.3)
        except Exception as e:
            log.warning("Could not snapshot %s: %s", ticker, e)

    log.info("Snapshotted %d/%d markets for race %d", saved, len(markets), race_id)
    return saved


def refresh_prediction_prices(race_id: int) -> int:
    """Update kalshi_mid_price and edge on prediction rows from latest orderbook snapshots."""
    from tools.db import cursor

    with cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (m.id)
                m.id AS market_id,
                s.best_yes_bid,
                s.best_yes_ask
            FROM markets m
            JOIN orderbook_snapshots s ON s.market_id = m.id
            WHERE m.race_id = %s
            ORDER BY m.id, s.snapshot_at DESC
        """, (race_id,))
        snapshots = cur.fetchall()

    if not snapshots:
        return 0

    updated = 0
    with cursor() as cur:
        for market_id, best_bid, best_ask in snapshots:
            mid = _compute_mid(best_bid, best_ask)
            if mid is None:
                continue
            if DRY_RUN:
                log.info("[DRY RUN] Would refresh market %d mid=%.3f", market_id, mid)
                updated += 1
                continue
            cur.execute("""
                UPDATE predictions
                SET kalshi_mid_price = %s,
                    edge = oracle_probability - %s
                WHERE id = (
                    SELECT id FROM predictions
                    WHERE market_id = %s
                    ORDER BY predicted_at DESC
                    LIMIT 1
                )
            """, (mid, mid, market_id))
            updated += 1

    log.info("Refreshed prices for %d markets in race %d", updated, race_id)
    return updated


# ─────────────────────────────────────────────────────────────────────────────
# Weather helper
# ─────────────────────────────────────────────────────────────────────────────

def get_race_weather(circuit: str, race_date_utc) -> bool:
    from tools.fetch_weather import fetch_weather
    from tools.circuit_locations import CIRCUIT_LOCATIONS

    coords = CIRCUIT_LOCATIONS.get(circuit)
    if not coords:
        log.warning("No lat/lon for circuit '%s' — defaulting is_wet=False", circuit)
        return False

    date_str = race_date_utc.strftime("%Y-%m-%d") if hasattr(race_date_utc, "strftime") else str(race_date_utc)[:10]
    try:
        result = fetch_weather(coords[0], coords[1], date_str)
        log.info("Weather for %s on %s: %.1fmm precipitation, is_wet=%s",
                 circuit, date_str, result["precipitation_mm"], result["is_wet"])
        return result["is_wet"]
    except Exception as e:
        log.warning("Weather fetch failed for %s: %s — defaulting is_wet=False", circuit, e)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestration state machine
# ─────────────────────────────────────────────────────────────────────────────

def orchestrate(race_id: int | None = None):
    race = find_target_race(race_id)
    if not race:
        log.info("No active race weekend found within 7-day window — nothing to do")
        return

    log.info("Target race: %s (id=%d, %s R%d, status=%s)",
             race["name"], race["id"], race["season"], race["round"], race["status"])

    rid = race["id"]
    race_dt = race["race_date_utc"]
    if hasattr(race_dt, "tzinfo") and not race_dt.tzinfo:
        race_dt = race_dt.replace(tzinfo=timezone.utc)

    # ── 1. Market discovery ────────────────────────────────────────────────
    if not markets_exist_for_race(rid) and race["status"] != "completed":
        if in_market_discovery_window(race):
            log.info("Step: discover Kalshi markets")
            n = discover_and_save_markets(race)
            log.info("Market discovery: saved %d market entries", n)
        else:
            log.info("Market discovery window not open yet (race is %s)", race_dt.date())
    elif race["status"] == "completed" and not markets_exist_for_race(rid):
        log.info("Race already completed with no markets — skipping discovery")
    else:
        log.info("Markets exist — skipping discovery")

    # ── 2. Orderbook snapshot + price refresh ──────────────────────────────
    if markets_exist_for_race(rid):
        log.info("Step: snapshot orderbook")
        snapshot_and_persist_orderbook(rid)
        if predictions_exist(rid):
            log.info("Step: refresh prediction prices")
            refresh_prediction_prices(rid)
    else:
        log.info("No markets yet — skipping orderbook snapshot")

    # ── 3. Qualifying ingest ───────────────────────────────────────────────
    if not qualifying_results_exist(rid):
        if in_qualifying_window(race):
            log.info("Step: ingest qualifying results")
            if DRY_RUN:
                log.info("[DRY RUN] Would run ingest(season=%d, round=%d, session=Q)",
                         race["season"], race["round"])
            else:
                try:
                    from tools.ingest_fastf1 import ingest
                    ingest(race["season"], race["round"], "Q")
                    log.info("Qualifying ingested successfully")
                except Exception as e:
                    log.info("Qualifying not ready in FastF1 yet: %s", e)
        else:
            log.info("Not in qualifying window yet — skipping")
    else:
        log.info("Qualifying results exist — skipping ingest")

    # ── 4. Model run ───────────────────────────────────────────────────────
    if qualifying_results_exist(rid) and not predictions_exist(rid):
        log.info("Step: run Oracle model")
        is_wet = get_race_weather(race["circuit"], race_dt)
        if DRY_RUN:
            log.info("[DRY RUN] Would run model for %s R%d (is_wet=%s)",
                     race["season"], race["round"], is_wet)
        else:
            try:
                from tools.run_model import run_race
                run_race(race["season"], race["round"], ALL_MARKET_TYPES, is_wet=is_wet)
                log.info("Model run complete")
            except Exception as e:
                log.error("Model run failed: %s", e)
    elif predictions_exist(rid):
        log.info("Predictions exist — skipping model run")

    # ── 5. Sprint ingest (sprint weekends only) ────────────────────────────
    if race["is_sprint_weekend"] and in_sprint_window(race):
        log.info("Step: ingest sprint results")
        if DRY_RUN:
            log.info("[DRY RUN] Would run ingest(season=%d, round=%d, session=S)",
                     race["season"], race["round"])
        else:
            try:
                from tools.ingest_fastf1 import ingest
                ingest(race["season"], race["round"], "S")
                log.info("Sprint ingested successfully")
            except Exception as e:
                log.info("Sprint not ready yet: %s", e)

    # ── 6. Race result ingest ──────────────────────────────────────────────
    if not race_results_exist(rid):
        if in_race_result_window(race):
            log.info("Step: ingest race results")
            if DRY_RUN:
                log.info("[DRY RUN] Would run ingest(season=%d, round=%d, session=R)",
                         race["season"], race["round"])
            else:
                try:
                    from tools.ingest_fastf1 import ingest
                    ingest(race["season"], race["round"], "R")
                    log.info("Race results ingested successfully")
                except Exception as e:
                    log.info("Race results not ready in FastF1 yet: %s", e)
        else:
            log.info("Not in race result window yet — skipping")
    else:
        log.info("Race results exist — skipping ingest")

    # ── 7. Settlement ──────────────────────────────────────────────────────
    if race_results_exist(rid) and not outcomes_settled(rid):
        log.info("Step: settle outcomes")
        if DRY_RUN:
            log.info("[DRY RUN] Would settle outcomes for race %d", rid)
        else:
            try:
                from tools.settle_outcomes import settle_race
                settle_race(rid)
                log.info("Outcomes settled")
            except Exception as e:
                log.error("Settlement failed: %s", e)
    elif outcomes_settled(rid):
        log.info("Outcomes already settled — skipping")

    # ── 8. Portfolio update ────────────────────────────────────────────────
    if outcomes_settled(rid) and not portfolio_snapshot_exists(rid):
        log.info("Step: update portfolio snapshot")
        if DRY_RUN:
            log.info("[DRY RUN] Would update portfolio for race %d", rid)
        else:
            try:
                from tools.update_portfolio import compute_and_save
                compute_and_save(rid)
                log.info("Portfolio updated")
            except Exception as e:
                log.error("Portfolio update failed: %s", e)
    elif portfolio_snapshot_exists(rid):
        log.info("Portfolio snapshot exists — skipping")

    log.info("Orchestration complete for %s", race["name"])


def main():
    parser = argparse.ArgumentParser(description="F1 Oracle pipeline orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without writing to DB")
    parser.add_argument("--race-id", type=int, default=None, help="Force a specific race ID")
    args = parser.parse_args()

    global DRY_RUN
    if args.dry_run:
        DRY_RUN = True

    if DRY_RUN:
        log.info("=== DRY RUN MODE — no DB writes ===")

    orchestrate(args.race_id)


if __name__ == "__main__":
    main()
