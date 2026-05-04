"""
Refresh Kalshi market prices for the current race weekend.

Snapshots the current orderbook for all open markets, then updates
kalshi_mid_price + edge on prediction rows. No-op if no race is in window.

Usage:
    python -m tools.refresh_prices
    DRY_RUN=true python -m tools.refresh_prices
"""

import logging
import os
import sys

import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("refresh_prices")


def find_active_race_id() -> int | None:
    """Return race ID if a race is within the refresh window, else None."""
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM races
                WHERE race_date_utc BETWEEN NOW() - INTERVAL '3 days'
                                       AND NOW() + INTERVAL '8 days'
                  AND status IN ('upcoming', 'active')
                ORDER BY race_date_utc ASC
                LIMIT 1
            """)
            row = cur.fetchone()
    return row[0] if row else None


def main():
    race_id = find_active_race_id()
    if not race_id:
        log.info("No race in window — skipping")
        sys.exit(0)

    log.info("Race %d in window — refreshing prices", race_id)

    # Import here so DRY_RUN env var is already set before orchestrate loads
    from tools.orchestrate import snapshot_and_persist_orderbook, refresh_prediction_prices

    snapped = snapshot_and_persist_orderbook(race_id)
    log.info("Snapshotted %d markets", snapped)

    if snapped > 0:
        updated = refresh_prediction_prices(race_id)
        log.info("Updated %d prediction prices", updated)
    else:
        log.info("No markets snapshotted — skipping price refresh")


if __name__ == "__main__":
    main()
