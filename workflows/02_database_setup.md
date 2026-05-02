# Workflow: Database Setup

## Objective
Initialize the Postgres database with the full schema required for Phase 1.

## Required Inputs
- `DATABASE_URL` in `.env`
- Postgres instance running (local or cloud)

## Steps
1. Run `tools/db_init.py` — creates all tables if they don't exist (idempotent)
2. Verify schema with `tools/db_verify.py` — prints table names and row counts

## Schema Overview

### `races`
Race weekend metadata (race_id, name, circuit, date_utc, country, timezone).

### `markets`
Kalshi market metadata (ticker, event_ticker, title, category, race_id, status, close_time).

### `predictions`
Model outputs (race_id, market_ticker, driver, model_probability, calibrated_probability, predicted_at, model_version).

### `orders`
Every order placed or considered (order_id, client_order_id, market_ticker, side, action, count, yes_price, status, placed_at, kalshi_response, edge, sizing_inputs, compliance_passed).

### `outcomes`
Settled results (race_id, market_ticker, resolved_at, winning_side, our_pnl).

### `learning_records`
Post-race learning cycle outputs (race_id, brier_score, calibration_json, strategy_params_json, lessons_json, created_at).

### `lessons`
Individual lessons from post-mortem agent (lesson_id, race_id, category, severity, description, proposed_action, times_seen, created_at, last_seen_at).

## Notes
- All timestamps stored as UTC
- `client_order_id` format: `{race_weekend}_{market_ticker}_{decision_timestamp_unix}`
- Schema migrations via Alembic (add as complexity grows)
