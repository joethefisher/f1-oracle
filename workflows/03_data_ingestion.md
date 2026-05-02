# Workflow: Data Ingestion

## Objective
Pull F1 session data and Kalshi market state into the feature store (Postgres).

## Required Inputs
- `DATABASE_URL` in `.env`
- `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PEM` in `.env`
- Race weekend identifier (e.g., `2026_monaco`)

## Steps

### F1 Historical Data (run once per race week)
1. `tools/ingest_fastf1.py --race {race_id}` — pulls qualifying + race session data for the target circuit from FastF1 cache
2. `tools/ingest_historical.py --circuit {circuit_key}` — pulls last 3 years of results at this circuit from Jolpica API
3. Results written to `.tmp/features_{race_id}.json` and loaded into `feature_store` table

### Kalshi Market Discovery (run Monday of race week)
1. `tools/discover_markets.py --race {race_id}` — queries Kalshi for all open F1 markets matching the weekend
2. Stores market metadata in `markets` table
3. Logs any markets that are missing (expected vs. found)

### Weather (run pre-qualifying and pre-race)
1. `tools/ingest_weather.py --circuit {circuit_key}` — pulls Open-Meteo forecast for circuit location
2. Appends to feature store

### Live Market Prices (run on schedule during race week)
1. `tools/snapshot_orderbook.py --race {race_id}` — snapshots order book for all active markets
2. Stored in `market_snapshots` table — this is the backtest dataset

## Schedule
| When | Tool |
|------|------|
| Monday | discover_markets, ingest_historical, ingest_fastf1 (practice 1 if available) |
| After each practice | ingest_fastf1 |
| Pre-qualifying | ingest_weather, snapshot_orderbook |
| Post-qualifying | ingest_fastf1 (qualifying session) |
| Pre-race (T-2h) | ingest_weather, snapshot_orderbook |

## Error Handling
- FastF1 cache miss: session data not yet available, retry after 2 hours
- Kalshi returns no markets: log and retry every 6 hours
- Jolpica 429: exponential backoff, no retries beyond 3 attempts

## Notes
- FastF1 downloads to local cache (~/.fastf1/cache). First run for a session takes 2-5 min.
- Keep `.tmp/` contents as backups during active race weekend; clear after settlement
