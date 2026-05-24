# F1 Oracle

A public ML model that predicts Formula 1 race outcomes and competes against [Kalshi](https://kalshi.com) prediction market prices. The Oracle publishes probability estimates, places virtual bets each race weekend, and grades itself after every race. The question it's trying to answer: does having a model beat following the crowd?

**Live site:** [joeking.ai/f1-oracle](https://joeking.ai/f1-oracle)

---

## What it does

Every F1 race weekend, the Oracle:

1. Ingests qualifying results via [FastF1](https://github.com/theOehrly/Fast-F1)
2. Snapshots live Kalshi market prices
3. Runs a calibrated logistic regression model to produce win/podium/pole probabilities per driver
4. Places virtual half-Kelly bets on markets where the model edge over Kalshi mid-price exceeds 5%
5. After the race, settles outcomes and updates the portfolio

The full pipeline runs automatically on GitHub Actions during race weekends.

---

## Tabs

| Tab | What it shows |
|-----|---------------|
| **Race Weekend** | Oracle probabilities vs. Kalshi market prices for the current race |
| **Season Record** | Every past prediction with win/loss result and P&L |
| **Portfolio** | Cumulative virtual $1,000 portfolio vs. a Kalshi crowd baseline |

---

## Model

**v2: Calibrated Logistic Regression with Elo ratings**

Features:
- `grid_pos_norm` — qualifying position normalized 0 (pole) to 1 (last)
- `driver_elo` — pairwise race Elo updated after every result (K=16)
- `constructor_elo` — pairwise qualifying Elo per constructor (K=8)
- `circuit_history` — driver's average finish at this circuit over the prior 3 seasons
- `is_street_circuit` — binary flag
- `is_wet` — wet conditions flag

Trained on F1 results from 2021 to present. Calibrated with `CalibratedClassifierCV` using Platt scaling so probabilities are well-formed before comparing against Kalshi prices.

Training corpus: ~2,100 driver-race rows across ~115 races.

---

## Virtual portfolio rules

- Starting bankroll: **$1,000**
- Bet sizing: **half-Kelly** based on edge over Kalshi mid-price
- Minimum edge to bet: **5%**
- Markets: race winner, podium finish, pole position

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| ML model | scikit-learn (logistic regression + Platt calibration) |
| F1 data | [FastF1](https://github.com/theOehrly/Fast-F1), [Jolpica API](https://github.com/jolpica/jolpica-f1) |
| Market data | Kalshi public API |
| Database | Supabase (Postgres) |
| Frontend | Next.js 15 (App Router + RSC), Tailwind CSS v4, Recharts |
| Hosting | Vercel + GitHub Actions |
| Language | Python 3.12 (backend), TypeScript (frontend) |

---

## Project structure

```
tools/          Python scripts (data ingestion, model, portfolio)
workflows/      Markdown SOPs for each operation
tests/          108 pytest tests
web/            Next.js frontend
  app/
    race/       Race Weekend page
    record/     Season Record page
    portfolio/  Portfolio page
  lib/          Supabase queries, types
.github/
  workflows/    GitHub Actions cron jobs
```

---

## Self-hosting

### Prerequisites

- Python 3.12+, Node 20+
- A [Supabase](https://supabase.com) project
- No Kalshi account needed

### Setup

```bash
git clone https://github.com/<your-username>/f1-oracle.git
cd f1-oracle
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# add DATABASE_URL to .env

python -m tools.db_init

# ingest historical data (~10 min)
python -m tools.setup_season --season 2025
python -m tools.ingest_fastf1 --season 2025
python -m tools.ingest_historical --start-year 2021

python -m tools.build_training_data
python -m tools.setup_season --season 2026
```

### Running a race weekend manually

```bash
# after qualifying
python -m tools.save_markets --season 2026 --round 5
python -m tools.snapshot_orderbook --season 2026 --round 5
python -m tools.run_model --season 2026 --round 5

# after the race
python -m tools.ingest_fastf1 --season 2026 --round 5 --session R
python -m tools.settle_outcomes --season 2026 --round 5
python -m tools.update_portfolio --season 2026 --round 5
```

See `workflows/05_race_weekend.md` for the full procedure.

### Frontend

```bash
cd web
cp .env.local.example .env.local
# add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

npm install
npm run dev
```

### Automation

Add `DATABASE_URL` as a repository secret. The workflow in `.github/workflows/race_weekend.yml` runs every 30 minutes Thursday through Sunday, and once daily the rest of the week. A gate job checks for an active race week before running the full pipeline; it applies idempotent DB migrations, runs the orchestrator, and commits any retrained models back.

It runs **hands-off**: race status self-heals from facts, missing markets are discovered incrementally, and when the season runs out the next one is set up automatically.

### Notifications & health watchdog

With a Telegram bot configured (optional), the bot reports for itself:
- 🏁 **bets placed**, 🏆 **race & bet results**, and 💰 **portfolio standing vs the Kalshi-crowd baseline** at each weekend milestone;
- 🚨 **alerts** on crashes and — via the independent watchdog in `.github/workflows/health_check.yml` — on *silent* failures (e.g. a race weekend that produced no predictions). Alerts de-dupe, pinging once per problem.

Add these as repository secrets to enable it (leave unset to disable silently):
`TELEGRAM_API_TOKEN`, `TELEGRAM_CHAT_ID`. See `.env.example` for how to obtain them.

---

## Environment variables

```bash
# .env
DATABASE_URL=postgresql://...
TELEGRAM_API_TOKEN=        # optional — notifications
TELEGRAM_CHAT_ID=          # optional — notifications

# web/.env.local
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<your anon key>
```

---

## Tests

```bash
python -m pytest
cd web && npx tsc --noEmit
```

---

## License

MIT
