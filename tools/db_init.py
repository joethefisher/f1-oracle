"""
Create all F1 Oracle database tables. Safe to run multiple times (idempotent).

Usage:
    python tools/db_init.py
"""

from tools.db import cursor
from rich.console import Console

console = Console()

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    id                SERIAL PRIMARY KEY,
    season            INTEGER NOT NULL,
    round             INTEGER NOT NULL,
    name              TEXT NOT NULL,
    circuit           TEXT NOT NULL,
    race_date_utc     TIMESTAMPTZ,
    is_sprint_weekend BOOLEAN DEFAULT FALSE,
    status            TEXT NOT NULL DEFAULT 'upcoming',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (season, round)
);

CREATE TABLE IF NOT EXISTS markets (
    id                  SERIAL PRIMARY KEY,
    race_id             INTEGER REFERENCES races(id),
    kalshi_ticker       TEXT NOT NULL UNIQUE,
    kalshi_event_ticker TEXT NOT NULL,
    market_type         TEXT NOT NULL,
    driver_name         TEXT,
    driver_abbreviation VARCHAR(10),
    status              TEXT NOT NULL DEFAULT 'open',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id                 SERIAL PRIMARY KEY,
    market_id          INTEGER REFERENCES markets(id),
    oracle_probability NUMERIC(6,4) NOT NULL,
    -- kalshi_mid_price / edge are NULL when the market has no live price.
    -- We still store the Oracle's probability (the public site shows it), but
    -- never bet without a real price. See run_model.save_predictions_and_get_ids.
    kalshi_mid_price   NUMERIC(6,4),
    edge               NUMERIC(6,4),
    predicted_at       TIMESTAMPTZ DEFAULT NOW(),
    model_version      TEXT NOT NULL DEFAULT 'v1'
);

CREATE TABLE IF NOT EXISTS virtual_bets (
    id               SERIAL PRIMARY KEY,
    prediction_id    INTEGER REFERENCES predictions(id),
    bet_size_dollars NUMERIC(10,2) NOT NULL,
    kelly_fraction   NUMERIC(8,6) NOT NULL,
    bankroll_at_time NUMERIC(10,2) NOT NULL,
    placed_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outcomes (
    id           SERIAL PRIMARY KEY,
    market_id    INTEGER REFERENCES markets(id) UNIQUE,
    winning_side TEXT NOT NULL,
    settled_at   TIMESTAMPTZ DEFAULT NOW(),
    source       TEXT NOT NULL DEFAULT 'fastf1'
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                    SERIAL PRIMARY KEY,
    race_id               INTEGER REFERENCES races(id) UNIQUE,
    bankroll_after        NUMERIC(10,2) NOT NULL,
    return_pct            NUMERIC(8,4) NOT NULL,
    kalshi_baseline_value NUMERIC(10,2),
    snapshot_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS race_results (
    id            SERIAL PRIMARY KEY,
    race_id       INTEGER REFERENCES races(id),
    driver_number TEXT,
    abbreviation  TEXT,
    driver_name   TEXT NOT NULL,
    team_name     TEXT,
    position      INTEGER,
    grid_position INTEGER,
    status        TEXT,
    points        NUMERIC(6,2),
    UNIQUE (race_id, driver_number)
);

CREATE TABLE IF NOT EXISTS qualifying_results (
    id            SERIAL PRIMARY KEY,
    race_id       INTEGER REFERENCES races(id),
    driver_number TEXT,
    abbreviation  TEXT,
    driver_name   TEXT NOT NULL,
    team_name     TEXT,
    position      INTEGER,
    grid_position INTEGER,
    status        TEXT,
    points        NUMERIC(6,2),
    UNIQUE (race_id, driver_number)
);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id              SERIAL PRIMARY KEY,
    market_id       INTEGER REFERENCES markets(id),
    best_yes_bid    NUMERIC(6,4),
    best_yes_ask    NUMERIC(6,4),
    best_no_bid     NUMERIC(6,4),
    best_no_ask     NUMERIC(6,4),
    volume_24h      NUMERIC(12,2),
    snapshot_at     TIMESTAMPTZ DEFAULT NOW()
);
"""


# Idempotent migrations for already-created databases (CREATE TABLE IF NOT EXISTS
# never alters an existing table). Each statement is safe to re-run.
MIGRATIONS = """
ALTER TABLE predictions ALTER COLUMN kalshi_mid_price DROP NOT NULL;
ALTER TABLE predictions ALTER COLUMN edge DROP NOT NULL;
"""


def init_db():
    with cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute(MIGRATIONS)
    console.print("[green]Schema created successfully (9 tables).[/]")


if __name__ == "__main__":
    init_db()
