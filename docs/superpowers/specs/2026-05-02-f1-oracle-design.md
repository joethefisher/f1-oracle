# F1 Oracle — Design Spec
**Date:** 2026-05-02  
**Status:** Approved

---

## 1. Overview

F1 Oracle is a public, read-only website that runs an ML model against F1 race weekend prediction markets. Before each race it publishes probability estimates alongside Kalshi market prices, showing exactly where the model agrees and disagrees with the crowd. After each race it grades itself. Over the season it tracks a virtual $1,000 portfolio to answer one question: *does having a model beat following the crowd?*

No real money. No accounts. No user interaction. A public scorecard that updates itself each race weekend.

---

## 2. The Three Tabs

### Tab 1 — Race Weekend
Shows the Oracle's current predictions for the active race weekend, compared market-by-market against Kalshi's implied probabilities.

**Content:**
- Race name, circuit, date, weekend type (sprint or standard)
- Model last updated timestamp (e.g. "Post-qualifying · 2h ago")
- Sub-market selector: Race Winner · Podium · Pole Position · Sprint (when applicable)
- Per-driver table for selected market:
  - Driver name
  - Visual bar showing Oracle probability vs Kalshi mid-price
  - Oracle % column
  - Kalshi % column
  - Edge column: "+7% ↑" in green when Oracle is higher, "−7% ↓" in red when Oracle is lower, "—" when within 2%
- Drivers sorted by Oracle probability descending
- Between races: shows the most recent race results and a "Next race in X days" countdown

**Market mid-price calculation:**  
`kalshi_mid = (yes_bid + yes_ask) / 2`. When bid is absent, use ask only.

### Tab 2 — Season Record
A log of every prediction the Oracle made, graded after each race.

**Content:**
- Season summary row: total predictions, correct %, virtual P&L to date
- Race-by-race expandable sections, most recent first
- Each prediction row:
  - Market description (e.g. "Norris to WIN · Miami GP")
  - Oracle probability at time of prediction
  - Kalshi mid-price at time of prediction
  - Edge at time of prediction
  - Virtual bet size (half-Kelly dollars)
  - Outcome: WIN ✓ or LOSS ✗
  - P&L for that bet
- Settled races show aggregate: bets placed, wins, losses, net P&L

### Tab 3 — Portfolio
Virtual portfolio performance from $1,000 starting value, across the full season.

**Content:**
- Current portfolio value (large, prominent)
- Total return % since season start
- Line chart: Oracle portfolio value over time (one data point per race weekend)
- Second line on same chart: Average Kalshi bettor baseline (defined below)
- Races on x-axis, $ value on y-axis
- Below chart: race-by-race table showing portfolio value after each race weekend

**Average Kalshi bettor baseline:**  
A hypothetical bettor who places the same total dollar amount as Oracle each race weekend, spread proportionally across all markets according to Kalshi's implied probabilities. No edge detection — pure crowd-following. This is the passive benchmark Oracle is trying to beat.

---

## 3. Virtual Portfolio Rules

| Rule | Value |
|------|-------|
| Starting bankroll | $1,000 |
| Bet sizing | Half-Kelly |
| Minimum edge to bet | 5% above Kalshi mid-price |
| Maximum bet per market | 10% of current bankroll |
| Markets in scope | Race winner, podium, pole position, sprint winner |
| Settlement | After official race results confirmed via FastF1 |

**Half-Kelly formula:**  
```
edge = oracle_probability - kalshi_mid_price
kelly_fraction = edge / (1 - kalshi_mid_price)
bet_size = 0.5 * kelly_fraction * current_bankroll
bet_size = min(bet_size, 0.10 * current_bankroll)
```

Only bet when `edge >= 0.05` (5 percentage points).

---

## 4. Data Architecture

### Sources
| Source | What it provides | Auth |
|--------|-----------------|------|
| Kalshi public API | Market prices, order books | None |
| FastF1 | Qualifying results, race results, lap data, historical, settlement source | None |
| OpenF1 API | Live session fallback | None |
| Jolpica F1 API | Historical circuit data 1950–present | None |
| Open-Meteo | Circuit weather forecasts | None |

### Database (Supabase / Postgres)

**`races`**  
`id, name, circuit, round, season, race_date_utc, is_sprint_weekend, status (upcoming|active|completed)`

**`markets`**  
`id, race_id, kalshi_ticker, kalshi_event_ticker, market_type (race_winner|podium|pole|sprint), driver_name, status`

**`predictions`**  
`id, market_id, oracle_probability, kalshi_mid_price, edge, predicted_at, model_version`

**`virtual_bets`**  
`id, prediction_id, bet_size_dollars, kelly_fraction, bankroll_at_time, placed_at`

**`outcomes`**  
`id, market_id, winning_side (yes|no), settled_at, source (fastf1|manual)`

**`portfolio_snapshots`**  
`id, race_id, bankroll_after, return_pct, kalshi_baseline_value, snapshot_at`

---

## 5. Prediction Model

### Architecture
Multinomial logistic regression (conditional logit) across 20 drivers per market. One model per market type (race winner, podium, pole, sprint).

### Features (race winner model)
1. Qualifying position (strongest single predictor)
2. Driver average finish at this circuit (last 3 seasons)
3. Constructor pace deficit to fastest car at this circuit
4. Driver qualifying-to-finish delta (overtaking ability proxy)
5. Recent form: avg finish over last 3 races
6. Weather: binary dry/wet forecast
7. Championship pressure factor (position delta to leader)

### Calibration
Platt scaling applied to raw model outputs. Recalibrated after each race using cumulative prediction history.

### Update schedule
| Trigger | Action |
|---------|--------|
| Race week Monday | Retrain on all historical data, generate pre-weekend predictions |
| Post-qualifying | Rerun model with grid locked in, update predictions |
| Pre-race (T−2h) | Final weather check, lock predictions for the race |
| Post-race (Monday) | Settle outcomes, update calibration, log season record |

---

## 6. Tech Stack

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Database | Postgres via Supabase | Supabase (free tier) |
| Backend / agent | Python, WAT framework | Local / cron job |
| Frontend | Next.js 14 (App Router) | Vercel (free tier) |
| Charts | Recharts | — |
| Styling | Tailwind CSS | — |
| Data fetching | Server components + Supabase JS client | — |

### Frontend data access
Next.js server components query Supabase directly with the public (anon) read-only key. No API layer needed — the database is the API. Frontend is fully static between race weekends (ISR with 5-minute revalidation during active weekends, hourly otherwise).

---

## 7. Agent Update Cycle

The Python agent runs on a schedule (cron or manual trigger) and follows this cycle:

```
Race week Monday
  → tools/ingest_fastf1.py         (historical + practice data)
  → tools/discover_markets.py      (find active Kalshi markets for this race)
  → tools/run_model.py             (generate Oracle predictions)
  → tools/place_virtual_bets.py    (log half-Kelly virtual bets to DB)
  → tools/snapshot_orderbook.py    (snapshot Kalshi prices at prediction time)

Post-qualifying
  → tools/ingest_fastf1.py         (qualifying session data)
  → tools/run_model.py             (rerun with grid locked)
  → tools/update_predictions.py    (update prediction records)

Post-race Monday
  → tools/ingest_fastf1.py         (race session results)
  → tools/settle_outcomes.py       (match results to virtual bets, compute P&L)
  → tools/update_portfolio.py      (write portfolio_snapshot record)
  → tools/update_calibration.py    (recalibrate model on new data)
```

---

## 8. Build Phases

### Phase 1 — Foundation (current)
- [x] Kalshi public API exploration tools
- [ ] Supabase schema (db_init.py)
- [ ] FastF1 ingestion tool
- [ ] Market discovery + price snapshot on schedule

### Phase 2 — Prediction model
- [ ] Feature engineering pipeline
- [ ] Multinomial logit model (notebook first, then tool)
- [ ] Platt scaling calibration
- [ ] Historical backtest against known race outcomes

### Phase 3 — Virtual portfolio engine
- [ ] Half-Kelly bet sizing logic
- [ ] Virtual bet placement + logging
- [ ] Outcome settlement
- [ ] Portfolio snapshot computation + Kalshi baseline

### Phase 4 — Next.js frontend
- [ ] Project scaffold (Next.js + Tailwind + Supabase client)
- [ ] Tab 1: Race Weekend predictions table
- [ ] Tab 2: Season Record log
- [ ] Tab 3: Portfolio chart (Recharts)
- [ ] Responsive layout, dark theme
- [ ] Deploy to Vercel

### Phase 5 — Shadow mode
- [ ] 2–3 race weekends logging predictions without publishing publicly
- [ ] Validate model outputs look reasonable
- [ ] Fix calibration issues

### Phase 6 — Launch
- [ ] Make GitHub repo public
- [ ] Announce

---

## 9. Out of Scope
- Real money or Kalshi account
- User accounts or login
- In-race live markets
- Mobile app (responsive web only)
- Fastest lap, safety car, or other exotic markets
- Brier score or other calibration metrics on the public site
