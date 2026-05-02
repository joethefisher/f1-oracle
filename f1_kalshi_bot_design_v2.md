# F1 Kalshi Autonomous Betting Agent - Design Document v2

## 1. Project Overview

### Goal
Build a fully autonomous AI agent that participates in Kalshi's F1 race weekend prediction markets, **continuously learns from its own decisions**, and gets measurably stronger over the course of a season. The agent is given a fixed bankroll of $1,000, makes every decision independently, and operates without human approval gates.

### Reframing from v1
The bankroll is the substrate, not the point. With $1,000 funding 5-10 race weekends, this is fundamentally a learning system whose ground truth happens to be real bets. Success is defined by the agent's calibration improving from race 1 to race 10, not by PnL.

### Scope (v1)
- Agent only trades F1 race weekend markets on Kalshi
- Agent operates within a fixed bankroll, no top-ups
- Agent decides which markets to enter, sizing, timing, and exit
- Agent respects all Kalshi platform rules (position limits, rate limits, anti-manipulation policies)
- Agent runs a structured post-race learning cycle that updates its model and strategy parameters
- Agent maintains a dashboard showing its activity, reasoning, and evolving understanding

### Non-goals
- Profitability is not a v1 success criterion
- Beating sophisticated traders in efficient markets

### Success criteria
- Agent runs autonomously through 5+ race weekends without manual intervention
- All orders comply with Kalshi rules (no warnings, no flags)
- Calibration improves measurably between race 1 and race 5 (Brier score decreasing trend)
- Every decision the agent made is reviewable and explainable in the dashboard
- The "lessons learned" log shows at least 5 substantive insights surfaced by the post-mortem agent

## 2. System Architecture

### Eight-layer architecture
1. **Data ingestion layer** - Pulls F1 session data, weather, news, and Kalshi market state on a schedule
2. **Feature store** - Persists historical and current-weekend data in a structured format
3. **Prediction layer** - Generates calibrated probability estimates for each tradeable market
4. **Strategy layer** - Compares model probabilities to Kalshi prices, identifies edges, sizes bets
5. **Execution layer** - Places, monitors, amends, and cancels orders via Kalshi API
6. **Compliance and safety layer** - Enforces all platform rules and kill switches
7. **Learning and reflection layer** - Post-race analysis, model retraining, calibration updates, lessons learned
8. **Dashboard and observability layer** - Read-only interface showing agent activity, decisions, and growth

### Data flow during a race weekend
Data ingestion → Feature store → Prediction layer → Strategy layer → Compliance check → Execution → Outcomes logged → Learning layer (post-race) → Updated model and parameters → Next race uses improved system

### Persistence
Postgres database (recommended over SQLite for v1 because of concurrent reads from the dashboard). All state lives in the database. The agent is fully recoverable from a crash by reading from the store.

### Idempotency and crash recovery
Every order uses a deterministic `client_order_id` based on `{race_weekend}_{market_ticker}_{decision_timestamp}`. On startup, the agent reconciles its database against Kalshi's actual order state via `get_orders()` and `get_fills()`. Any mismatch is logged loudly. The agent never assumes its database matches Kalshi's reality without verification.

## 3. Kalshi API Integration

### SDK
Official `kalshi-python` SDK (v2.1.4+). Base URL: `https://api.elections.kalshi.com/trade-api/v2`.

### Authentication
RSA private key signing. API key ID and private key PEM stored in environment variables, never in code.

### Endpoints used
Same as v1 doc - `EventsApi`, `MarketsApi`, `PortfolioApi` covering market discovery, order book reading, balance checks, order placement, cancellation, and amendment.

### Order schema
```
ticker, side (yes/no), action (buy/sell), count, type (limit/market),
yes_price/no_price (1-99 cents), expiration_ts, buy_max_cost,
client_order_id (always set, deterministic)
```

### Market discovery
F1 markets identified by series ticker pattern. Agent enumerates available markets at the start of each race week and caches metadata.

## 4. F1 Data Sources

### Primary: FastF1 (Python library)
Full session telemetry, lap times, sector data, tire compound data, historical race results back to 2018. Free.

### Secondary: OpenF1 API
REST API alternative, useful as cross-check or live session fallback.

### Tertiary: Jolpica F1 API (Ergast successor)
Long-tail historical data going back to 1950 for circuit-specific analysis.

### Weather
Open-Meteo for circuit location forecasts.

### News and qualitative signals (v2)
RSS feeds from Autosport, The Race, Motorsport.com.

## 5. The Prediction Model (Properly Specified)

### Model formulation
The race winner market is fundamentally a **multi-class classification problem** across 20 drivers. Three valid approaches:

**Approach A: Conditional logit / softmax model.** Single model that takes per-driver features and outputs a probability distribution summing to 1 across the field. Standard in horse-racing literature. **Recommended for v1.**

**Approach B: Per-driver binary models with calibration normalization.** Fit a logistic regression per driver, then normalize outputs to sum to 1. Simpler to debug per driver but requires post-hoc calibration.

**Approach C: Gradient boosted trees (XGBoost/LightGBM) with multi-class objective.** Higher capacity but harder to interpret. Reserved for v2 once we see where v1 fails.

### Features for the race winner model (v1)
- Qualifying position (most predictive single variable)
- Driver's average finish position at this circuit over last 3 years
- Constructor's average pace deficit to fastest car at this circuit
- Driver's average qualifying-to-finish position delta (overtaking ability)
- Recent form (avg finish over last 3 races)
- Tire degradation index for the circuit
- Weather forecast (binary: dry/wet)
- Championship pressure factor (driver position relative to championship leader)

### Constructor markets
Derived from the race winner model. Expected constructor points = sum across both drivers of (P(finish position k) × points awarded for position k). Calibrated against historical constructor-level variance.

### Sprint race markets
Separate model with same architecture but trained only on sprint race data. Lower weight on tire-related features (irrelevant at sprint length), higher weight on raw qualifying pace.

### Calibration layer
Raw model outputs are passed through a calibration function (Platt scaling or isotonic regression) fit on rolling validation data. This is the critical piece I missed in v1: raw model probabilities are usually overconfident. The calibration layer corrects them and is itself updated after each race.

## 6. Agent Decision Loop

### Trigger schedule (timezone-aware)
All session times converted to UTC at race weekend start. Agent uses circuit-local timezone metadata from the F1 calendar API.

| Phase | Action |
|-------|--------|
| Race week Monday (UTC) | Pull race metadata, refresh historical features, identify active Kalshi markets |
| Each practice session | Update lap pace and tire data features |
| Pre-qualifying | Run model with practice data, place pre-quali bets if edge exists |
| Post-qualifying | **Major model rerun with grid locked in. Largest betting opportunity.** |
| Pre-race (T-2 hours) | Final weather check, news scan, last-look on positions |
| During race | Idle (no in-race markets in v1) |
| Post-race (T+2 hours after results final) | Settle positions, log outcomes |
| Race weekend Monday | **Run learning cycle (see Section 9)** |

### Edge detection
For each market: `edge = calibrated_model_probability - market_implied_probability`. Bet only when edge > threshold AND order book has sufficient liquidity at target price.

### Order book aware sizing
Sizing checks: (a) bankroll cap (5% per bet), (b) Kelly fraction based on edge, (c) **available liquidity at target price in the order book**. Take the minimum of the three.

### Confidence-weighted sizing
The Kelly fraction is multiplied by a confidence factor `c ∈ [0, 1]` derived from the model's predicted variance. Wide-uncertainty predictions get smaller bets even with the same point edge.

### Correlated exposure caps
Bets clustered by "race weekend outcome": all bets on Verstappen winning, McLaren constructor leading, Verstappen pole, etc. share an exposure budget. Total cluster exposure capped at 15% of bankroll. Total weekend exposure capped at 25%.

### Exit logic (v1)
Hold to settlement. No active management of open positions during the race.

## 7. Race Weekend Workflow

### Markets in scope for v1
- Race winner (per driver, yes/no)
- Constructor scoring most points (per team, yes/no)
- Driver podium finish (yes/no per driver)
- Sprint race winner (when sprint weekend)
- Pole position (limited window, pre-qualifying only)

### Markets out of scope for v1
- Safety car / red flag (high variance, hard to model)
- Lap-by-lap or in-race markets
- Fastest lap

### Exception handling (the cases I missed in v1)
- **No F1 markets posted yet:** Agent waits and re-polls every 6 hours. Logs the absence.
- **Market suspended mid-weekend:** Agent removes from candidate list, logs the event, does not attempt to place new orders on that market.
- **Driver replacement (e.g., reserve driver):** Agent flags the market for "qualitative review" status and applies a confidence haircut. Reserve drivers have insufficient model data, so the agent biases toward not betting these markets.
- **Session cancellation:** If qualifying is cancelled, agent uses Friday practice data as a fallback signal but applies a major confidence haircut (multiply Kelly fraction by 0.3).

## 8. Compliance and Safety Layer (Numerically Specified)

### Hard caps (numeric)
- Max single bet size: 5% of current bankroll, recomputed live before every order
- Max total exposure across open positions: 25% of bankroll
- Max correlated cluster exposure: 15% of bankroll
- Max bets per race weekend: 15
- Max position per Kalshi market: 80% of Kalshi's per-market position limit (build in headroom)
- Min bet size: $5 (avoid trivial orders that pollute the log)

### Rate limiting (numeric)
- Read API calls: max 50 per minute (Kalshi documented limit higher)
- Order placement: max 10 per minute
- 50ms minimum jitter between sequential calls
- Exponential backoff on 429 responses

### Anti-manipulation guards (numeric)
- No order on opposite side of same market within 60 seconds of a trade
- No cancel-and-replace at same price within 30 seconds
- No order whose limit price is more than 10 cents away from best bid/ask
- No order whose size is more than 30% of the visible book at that price level

### Kill switches
- Bankroll drops below $200 (80% drawdown): halt new bets, settle existing positions
- 3 consecutive negative race weekends: enter "review mode", pause until manual restart
- Hard API error (auth failure, account flag): immediate halt + alert
- Unexpected position state: halt and require manual reconciliation

### Logging
Every decision logged with: timestamp, market state, model probability, edge, sizing inputs, compliance check results, order placed (or skipped), Kalshi response. This log is the foundation for the learning layer and the dashboard.

## 9. Learning and Reflection Layer (The Core of v2)

This is the layer that makes the agent improve over time. It runs as a structured weekly cycle every Monday after a race weekend.

### Cycle steps

**Step 1: Outcome reconciliation**
- Pull final race results from FastF1
- Settle every open position based on actual outcomes
- Compute realized PnL per bet and per cluster
- Log everything to the learning database

**Step 2: Model parameter retraining**
- v1 approach: full retrain from scratch on the entire historical dataset including the latest race
- Cheap to compute for the simple model. No incremental drift bugs.
- v2 evolution: incremental Bayesian updates if full retrain becomes expensive

**Step 3: Calibration curve update**
- For predictions made in the last race, compute calibration metrics:
  - Brier score (overall accuracy + calibration)
  - Reliability diagram (predicted vs. actual hit rate per probability bin)
  - Log loss
- Update the rolling calibration function (Platt scaling or isotonic regression) used by the prediction layer
- Track Brier score over time. **Decreasing Brier score = the agent is getting smarter.** This is the headline learning metric.

**Step 4: Strategy parameter analysis**
- Grid search over historical decisions: would different edge thresholds (3%, 4%, 5%, 6%, 7%) have produced better PnL?
- Same for Kelly fraction caps and max-bets-per-weekend
- Track optimal parameters over time. After ~5 weekends of data, gradually shift live parameters toward the historically optimal values (with smoothing to avoid wild swings)

**Step 5: Post-mortem agent analysis**
This is where LLM reasoning enters the loop. A separate "post-mortem agent" (likely Claude via API, or a local model) reviews the weekend with structured prompts:

For every losing bet, it answers:
- Was the model's probability estimate wrong, the bet sizing wrong, or was this a correctly-placed bet that got unlucky?
- What signal, if any, should have warned us off this bet?
- Is there a pattern across multiple losing bets this weekend?

For every winning bet:
- Was this a skilled prediction or lucky outcome?
- Is the model giving credit to the right features for this win?

For markets we did not bet but which had edge:
- What threshold or signal caused us to skip? Was that justified given the outcome?

The post-mortem agent's output is structured: a "Lessons Learned" record with categories (model error, sizing error, missed opportunity, false positive, etc.), severity, and a proposed action (retrain feature X, adjust parameter Y, add feature Z to candidate list).

**Step 6: Lessons learned database**
- Every lesson is stored permanently
- Lessons that recur across weekends get elevated severity
- After 3 weekends with the same lesson recurring, the system flags it for human review (via dashboard notification, not approval gate)
- Lessons can include proposed new features for the model

**Step 7: Feature candidate evaluation**
- Proposed new features from post-mortems get added to a candidate list
- After enough data, candidate features are A/B tested: train one model with the feature, one without, compare validation performance
- Winning candidates get promoted into the live model

**Step 8: Race prep for next weekend**
- With updated model, calibration, parameters, and lessons, the agent begins prep for the next race
- Cycle continues

### What this gives us
- The model literally has different parameters after every race
- Calibration is corrected based on actual outcomes
- Strategy parameters drift toward what's historically worked
- Failure patterns get surfaced and acted upon
- New features can be discovered and tested without manual intervention

### What "getting stronger" means concretely
Brier score on race winner predictions trending down across the season. Calibration curves moving closer to the diagonal. ROI improving (even if still negative). Lessons learned database populating with non-trivial insights.

## 10. Dashboard and Observability Layer

### Why this is in v1 scope
You need to see what the agent is doing, why, and what it's learning. Without this, the agent is a black box that loses $1,000 over 5 weekends without producing transferrable knowledge. The dashboard is what converts raw activity into a learning artifact.

### Implementation
- Next.js or Streamlit web app (Streamlit faster to ship, Next.js more polished)
- Read-only frontend on the same Postgres database the agent writes to
- Authenticated, deployed alongside the agent on the same cloud host
- No write actions - the dashboard is observability, not control

### Views

**Live view**
- Current bankroll, current PnL (vs. starting $1,000)
- Open positions with real-time mark-to-market
- Most recent decisions (last 24 hours) with one-line summaries
- Agent status (idle, ingesting data, predicting, executing, learning, halted)
- Next scheduled action and time

**Race weekend view**
- Timeline of a specific race weekend, Monday through Sunday
- Every decision the agent made annotated with reasoning
- Each bet shown as a card: market, side, size, price, edge, reasoning, current status, settled outcome
- Click any bet to expand into full reasoning tree (model probability, calibration adjustment, edge calc, sizing inputs, compliance checks)

**Historical view**
- Season-level PnL chart
- Win rate by market type
- Model calibration over time (Brier score trend - **the headline learning metric**)
- ROI by race weekend
- Largest wins and largest losses with full reasoning available

**Learning Journal view (the most important)**
- Calibration curves over time, animated to show evolution
- Lessons Learned log with filter and search
- Strategy parameter changes timeline (when and why each parameter shifted)
- Feature additions to the model with their A/B test results
- Brier score trend chart with annotations for major model changes

**Compliance log**
- Every order with compliance check results
- Any kill switch triggers
- Rate limiting events
- Reconciliation events on agent startup

## 11. Build Phases (Restructured)

### Phase 1: Foundation (week 1)
- Kalshi sandbox account and API credentials
- Postgres database with schema
- Data ingestion layer for FastF1 and Kalshi
- Idempotency and reconciliation logic
- Auth and basic API calls verified end-to-end

### Phase 2: Prediction model (weeks 2-3)
- v1 multinomial model in a notebook, validated against historical races
- Calibration layer (Platt scaling) with rolling validation
- Backtest the **prediction model** against historical race outcomes (not Kalshi prices, just race outcomes)
- Port to the agent's prediction layer

### Phase 3: Strategy and execution (week 4)
- Edge detection, sizing logic, correlated exposure caps
- Order placement, monitoring, cancellation, amendment
- Full compliance layer with numeric thresholds

### Phase 4: Dashboard (week 5)
- Build before going live, not after
- All five views functional
- Connected to the same database the agent uses

### Phase 5: Shadow mode (weeks 6-8)
- 2-3 race weekends running the full agent loop with no real orders
- Agent logs every decision it would have made
- Compare predictions to outcomes to validate calibration before risking money
- Refine model based on shadow mode results

### Phase 6: Learning layer build (week 9)
- Post-mortem agent integration
- Calibration update cycle
- Strategy parameter analysis
- Lessons Learned database

### Phase 7: Live deployment (week 10)
- Switch to production credentials
- Fund $1,000
- Deploy on cloud host (Fly.io, Railway)
- First live race weekend with full monitoring

### Phase 8: Continuous learning (ongoing)
- Weekly learning cycle runs every Monday
- Model improves over time
- Dashboard shows growth

## 12. Open Implementation Questions

These resolve in Claude Code, not in design:
- Hosting: cloud VM, serverless, or managed platform like Fly.io
- Notification stack: Slack webhook for major events, daily email summary
- Stripe wallet integration: defer to v2. Fund Kalshi directly via ACH for v1 simplicity.
- Backtesting market price data: Kalshi may not expose historical prices via API. Start logging market prices ourselves in Phase 1 so we have a backtesting dataset by Phase 5.
- Post-mortem agent: Claude API (highest quality, costs ~$1-5 per weekend) vs. local open model (free but lower quality). Recommend Claude API for v1.

## 13. Risk Register

- **Cold start risk:** First race has no agent-specific calibration data. Mitigated by shadow mode phase.
- **Model staleness:** 2026 cars/rules differ from training data. Mitigated by full retrain after every race and explicit recency weighting in feature engineering.
- **Liquidity risk:** F1 markets may be too thin for meaningful position sizing. If observed, agent reduces minimum bet size or skips low-liquidity markets entirely.
- **Reconciliation failures:** Agent state diverges from Kalshi. Mitigated by mandatory reconciliation on every startup with halt-on-mismatch.
- **Kalshi platform risk:** Account flag, rule changes, market suspension. Mitigated by conservative compliance layer.
- **Learning feedback loop risk:** Agent overfits to small sample of recent races and degrades. Mitigated by full retrain on entire history (not just recent), and by smoothed parameter updates rather than abrupt shifts.
- **Cost risk:** Post-mortem agent (Claude API) costs accumulate. Capped at $20/weekend budget.

## 14. The Bigger Picture

The artifact at the end of the season is not the bot's PnL. It's a system that demonstrably learned. The Brier score chart bending downward, the lessons learned database populated with insights you can read and learn from, the calibration curves moving toward perfect, the strategy parameters that converged to what actually works.

If the bankroll happens to grow, that's a bonus. If it goes to zero, the value is still in the documented evolution of the agent's understanding. That's the project.
