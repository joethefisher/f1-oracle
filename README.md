# F1 Oracle

A public ML model that predicts Formula 1 race outcomes and competes against [Kalshi](https://kalshi.com) prediction market prices. The Oracle publishes its probability estimates, places virtual bets on every race weekend, and grades itself after every race. No real money — it's a public scorecard answering one question: *does having a model beat following the crowd?*

**Live site:** [f1oracle.vercel.app](https://web-silk-xi-22.vercel.app)

---

## What it does

Every F1 race weekend, the Oracle:

1. Ingests qualifying results via [FastF1](https://github.com/theOehrly/Fast-F1)
2. Snapshots live Kalshi market prices (no auth required — Kalshi's public API)
3. Runs a calibrated logistic regression model to produce win/podium/pole probabilities for each driver
4. Places virtual half-Kelly bets on markets where its edge over the Kalshi mid-price exceeds 5%
5. After the race, settles outcomes and updates the portfolio

All of this runs automatically on GitHub Actions during race weekends.

---

## Three public tabs

| Tab | What it shows |
|-----|---------------|
| **Race Weekend** | Oracle probabilities vs. Kalshi market prices for the current race |
| **Season Record** | Every past prediction — win/loss result and P&L per race |
| **Portfolio** | Cumulative virtual $1,000 portfolio vs. a Kalshi crowd baseline |

---

## Model

**v2 — Calibrated Logistic Regression with Elo ratings**

Features:
- `grid_pos_norm` — qualifying position normalized 0 (pole) → 1 (last)
- `driver_elo` — pairwise race Elo, updated after every result (K=16)
- `constructor_elo` — pairwise qualifying Elo per constructor (K=8)
- `circuit_history` — driver's average finish at this circuit over the prior 3 seasons
- `is_street_circuit` — binary flag (Monaco, Baku, Singapore, Miami, etc.)
- `is_wet` — wet conditions flag

Trained on F1 results from 2021–present. Calibrated with `CalibratedClassifierCV` (Platt scaling) so the probabilities are meaningful before comparing to Kalshi prices.

Training corpus: ~2,100 driver-race rows across ~115 races.

---

## Virtual portfolio rules

- Starting bankroll: **$1,000**
- Bet sizing: **half-Kelly** based on edge over Kalshi mid-price
- Minimum edge to bet: **5%**
- Markets: race winner, podium finish (top 3), pole position
- No real money — virtual only

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| ML model | scikit-learn (logistic regression + Platt calibration) |
| F1 data | [FastF1](https://github.com/theOehrly/Fast-F1), [Jolpica API](https://github.com/jolpica/jolpica-f1) |
| Market data | Kalshi public API (unauthenticated) |
| Database | Supabase (Postgres) |
| Frontend | Next.js 16 (App Router + RSC), Tailwind CSS v4, Recharts |
| Hosting | Vercel (frontend) + GitHub Actions (automation) |
| Language | Python 3.12 (backend), TypeScript (frontend) |

---

## Project structure

```
tools/          Python scripts (data ingestion, model, portfolio)
workflows/      Markdown SOPs for each operation
tests/          108 pytest tests
web/            Next.js frontend (three tabs)
  app/
    race/       Race Weekend page
    record/     Season Record page
    portfolio/  Portfolio page
  lib/          Supabase queries, types
.github/
  workflows/    GitHub Actions (race weekend automation)
```

---

## Self-hosting

### Prerequisites

- Python 3.12+, Node 20+
- A [Supabase](https://supabase.com) project (free tier works)
- No Kalshi account required (public API only)

### Setup

```bash
# Clone and set up Python env
git clone https://github.com/<your-username>/f1-oracle.git
cd f1-oracle
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: add DATABASE_URL (Supabase direct connection string)

# Initialize database schema
python -m tools.db_init

# Ingest historical data (takes ~10 min — downloads from FastF1)
python -m tools.setup_season --season 2025
python -m tools.ingest_fastf1 --season 2025  # all rounds, Q + R sessions
python -m tools.ingest_historical --start-year 2021  # fills gaps via Jolpica

# Train models
python -m tools.build_training_data

# Set up the current season's race calendar
python -m tools.setup_season --season 2026
```

### Running a race weekend manually

```bash
# After qualifying — save markets and run the model
python -m tools.save_markets --season 2026 --round 5
python -m tools.snapshot_orderbook --season 2026 --round 5
python -m tools.run_model --season 2026 --round 5

# After the race — settle and update portfolio
python -m tools.ingest_fastf1 --season 2026 --round 5 --session R
python -m tools.settle_outcomes --season 2026 --round 5
python -m tools.update_portfolio --season 2026 --round 5
```

See `workflows/05_race_weekend.md` for the full annotated procedure.

### Frontend

```bash
cd web
cp .env.local.example .env.local
# Edit .env.local: add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

npm install
npm run dev     # http://localhost:3000
npm run build   # production build
```

### Automation (GitHub Actions)

Add `DATABASE_URL` as a repository secret. The workflow in `.github/workflows/race_weekend.yml` runs:
- Every 30 minutes Thursday–Sunday (race weekends)
- Once daily Monday–Wednesday (to catch pre-race market openings)

A lightweight gate job (`tools/race_gate.py`) checks for an active race week before running the full pipeline, keeping GitHub Actions minutes well under the free-tier limit.

---

## Environment variables

```bash
# .env (never committed)
DATABASE_URL=postgresql://...   # Supabase direct connection

# web/.env.local (never committed)
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<your anon/publishable key>
```

See `.env.example` and `web/.env.local.example` for full reference.

---

## Tests

```bash
python -m pytest          # 108 tests
cd web && npx tsc --noEmit  # TypeScript check
```

---

## License

MIT
