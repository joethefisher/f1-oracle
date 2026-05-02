# F1 Oracle

## Project Overview
A public website that runs an ML model against F1 race weekend prediction markets, grading itself after every race. Visitors can see the Oracle's probability estimates vs. Kalshi market prices, track its virtual $1,000 portfolio using half-Kelly bet sizing, and follow its season-long record. No real money — purely a public scorecard that answers: *does having a model beat following the crowd?*

## WAT Framework
This project follows the WAT (Workflows, Agents, Tools) architecture:
- `workflows/` — Markdown SOPs for each major operation
- `tools/` — Python scripts for deterministic execution
- `.tmp/` — Temporary processing files (regenerable, gitignored)
- `.env` — All secrets and API keys (gitignored, never in code)

## Three Public Tabs
1. **Race Weekend** — Oracle predictions vs Kalshi market prices, current race weekend. Sub-markets: race winner, podium, pole, sprint.
2. **Season Record** — Every past prediction with outcome (win/loss) and portfolio P&L impact.
3. **Portfolio** — Cumulative virtual portfolio curve from $1,000 starting value, half-Kelly sized bets.

## Virtual Portfolio Rules
- Starting bankroll: $1,000
- Bet sizing: half-Kelly based on Oracle edge over Kalshi mid-price
- Minimum edge to bet: 5% over Kalshi implied probability
- Markets in scope: race winner, podium, pole position, sprint winner
- Average Kalshi bettor baseline: same markets, bet proportional to Kalshi prices, shown on Portfolio tab for comparison

## Key Design Decisions
- **No real money** — virtual portfolio only, no Kalshi account required
- **Public, read-only** — no user accounts, no login
- **Kalshi public API** — all market data via unauthenticated endpoints
- **FastF1** — primary F1 data source for model features
- **Postgres (Supabase)** — all predictions, outcomes, portfolio state
- **Half-Kelly sizing** — full Kelly produces excessive variance for a public product

## Data Sources
- **Kalshi public API** — market prices, order books (no auth required)
- **FastF1** — telemetry, lap times, qualifying results, historical data
- **OpenF1 API** — fallback/cross-check
- **Jolpica F1 API** — historical circuit data back to 1950
- **Open-Meteo** — weather forecasts

## Environment Variables Required
```
DATABASE_URL=
ANTHROPIC_API_KEY=
```

## Build Phases
1. **Foundation** — Supabase schema, data ingestion, Kalshi public market snapshots
2. **Prediction model** — Multinomial model, calibration layer, historical backtest
3. **Virtual portfolio engine** — half-Kelly sizing, bet logging, outcome settlement
4. **Public website** — Next.js, three tabs, deployed to Vercel
5. **Shadow mode** — 2-3 race weekends logging predictions without publishing
6. **Launch** — go public, post-race grading cycle live
