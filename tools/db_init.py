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
    id                 SERIAL PRIMARY KEY,
    prediction_id      INTEGER REFERENCES predictions(id),
    bet_size_dollars   NUMERIC(10,2) NOT NULL,
    kelly_fraction     NUMERIC(8,6) NOT NULL,
    bankroll_at_time   NUMERIC(10,2) NOT NULL,
    -- The price the bot actually paid and the model's view at bet time. These
    -- are the source of truth for P&L and post-mortems; predictions.kalshi_mid_price
    -- is mutable (run_model upserts on every run) and not safe to rely on.
    kalshi_mid_at_bet  NUMERIC(6,4),
    oracle_prob_at_bet NUMERIC(6,4),
    placed_at          TIMESTAMPTZ DEFAULT NOW()
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

CREATE TABLE IF NOT EXISTS model_metrics (
    id             SERIAL PRIMARY KEY,
    race_id        INTEGER REFERENCES races(id),
    model_version  TEXT NOT NULL,
    market_type    TEXT NOT NULL,
    n              INTEGER NOT NULL,
    oracle_brier   NUMERIC(8,5),
    kalshi_brier   NUMERIC(8,5),
    oracle_logloss NUMERIC(8,5),
    kalshi_logloss NUMERIC(8,5),
    computed_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (race_id, model_version, market_type)
);

-- Open/resolved health-check alerts, so the watchdog pings once per problem
-- (not every run). check_key is a stable id like "260:no_predictions".
CREATE TABLE IF NOT EXISTS health_alerts (
    id          SERIAL PRIMARY KEY,
    check_key   TEXT NOT NULL UNIQUE,
    race_id     INTEGER,
    severity    TEXT,
    message     TEXT,
    opened_at   TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
"""


# Idempotent migrations for already-created databases (CREATE TABLE IF NOT EXISTS
# never alters an existing table). Each statement is safe to re-run.
MIGRATIONS = """
ALTER TABLE predictions ALTER COLUMN kalshi_mid_price DROP NOT NULL;
ALTER TABLE predictions ALTER COLUMN edge DROP NOT NULL;
ALTER TABLE virtual_bets ADD COLUMN IF NOT EXISTS kalshi_mid_at_bet  NUMERIC(6,4);
ALTER TABLE virtual_bets ADD COLUMN IF NOT EXISTS oracle_prob_at_bet NUMERIC(6,4);
"""

# Backfill bet-time price for historic rows from the nearest orderbook snapshot
# at/before placed_at. Idempotent: only fills NULLs, so re-runs are no-ops once
# populated. Predictions.kalshi_mid_price isn't trustworthy here — run_model
# overwrites it on every run, including post-race when the book has resolved.
BACKFILL_BET_PRICES = """
UPDATE virtual_bets vb
SET kalshi_mid_at_bet = sub.mid
FROM (
    SELECT DISTINCT ON (vb2.id) vb2.id,
        CASE
            WHEN os.best_yes_bid IS NOT NULL AND os.best_yes_ask IS NOT NULL
                THEN (os.best_yes_bid + os.best_yes_ask) / 2
            WHEN os.best_yes_ask IS NOT NULL THEN os.best_yes_ask
            WHEN os.best_yes_bid IS NOT NULL THEN os.best_yes_bid
            WHEN os.best_no_bid  IS NOT NULL THEN 1.0 - os.best_no_bid
        END AS mid
    FROM virtual_bets vb2
    JOIN predictions p2 ON vb2.prediction_id = p2.id
    JOIN orderbook_snapshots os ON os.market_id = p2.market_id
        AND os.snapshot_at <= vb2.placed_at
    WHERE vb2.kalshi_mid_at_bet IS NULL
    ORDER BY vb2.id, os.snapshot_at DESC
) sub
WHERE vb.id = sub.id AND vb.kalshi_mid_at_bet IS NULL;
"""


def init_db():
    with cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute(MIGRATIONS)
        cur.execute(BACKFILL_BET_PRICES)
    console.print("[green]Schema created successfully (11 tables).[/]")


if __name__ == "__main__":
    init_db()
