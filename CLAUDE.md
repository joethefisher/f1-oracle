# F1 Kalshi Autonomous Betting Agent

## Project Overview
Autonomous AI agent that participates in Kalshi F1 race weekend prediction markets, continuously learning from its own decisions. Fixed bankroll of $1,000. No human approval gates. See `f1_kalshi_bot_design_v2.md` for full design spec.

## WAT Framework
This project follows the WAT (Workflows, Agents, Tools) architecture:
- `workflows/` — Markdown SOPs for each major operation
- `tools/` — Python scripts for deterministic execution
- `.tmp/` — Temporary processing files (regenerable, gitignored)
- `.env` — All secrets and API keys (gitignored, never in code)

## Build Phases
1. **Foundation** — Kalshi auth, Postgres schema, data ingestion, reconciliation
2. **Prediction model** — Multinomial model, Platt scaling calibration, historical backtest
3. **Strategy and execution** — Edge detection, sizing, compliance layer
4. **Dashboard** — Read-only Streamlit/Next.js app against same Postgres DB
5. **Shadow mode** — 2-3 race weekends, no real orders, validate calibration
6. **Learning layer** — Post-mortem agent (Claude API), calibration updates, lessons DB
7. **Live deployment** — Production credentials, Fly.io or Railway
8. **Continuous learning** — Weekly Monday cycle ongoing

## Key Design Decisions
- **Postgres** over SQLite (concurrent dashboard reads)
- **Deterministic `client_order_id`**: `{race_weekend}_{market_ticker}_{decision_timestamp}`
- **Reconciliation on every startup** — never assume DB matches Kalshi reality
- **Calibration layer** (Platt scaling) — raw model probabilities are overconfident
- **Post-mortem agent** — Claude API (~$1-5/weekend), capped at $20/weekend
- **Hold to settlement** — no active in-race position management in v1

## Compliance Hard Caps
- Max single bet: 5% of current bankroll
- Max total open exposure: 25% of bankroll
- Max correlated cluster: 15% of bankroll
- Max bets/weekend: 15
- Kill switch: bankroll < $200 OR 3 consecutive negative weekends

## Rate Limits
- Read API: max 50/min, 50ms jitter minimum
- Order placement: max 10/min
- Exponential backoff on 429s

## Data Sources
- **FastF1** — primary (telemetry, lap times, historical results)
- **OpenF1 API** — fallback/cross-check
- **Jolpica F1 API** (Ergast successor) — historical circuit data
- **Open-Meteo** — weather forecasts

## Environment Variables Required
```
KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PEM=
KALSHI_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
DATABASE_URL=
ANTHROPIC_API_KEY=
```

## Success Metric
Brier score on race winner predictions trending down across the season. Not PnL.
