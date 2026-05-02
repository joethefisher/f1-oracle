# F1 Oracle — Blockers Requiring User Action

Items I could not complete autonomously. Work through these in order and then let me know — I can continue building immediately.

---

## BLOCKER 1: Supabase setup (Required before any live data)

**What's needed:**
1. Sign up at https://supabase.com and create a new project
2. Copy the `DATABASE_URL` (PostgreSQL connection string) from Project Settings → Database → Connection string → URI
3. Add it to `.env` in the project root:
   ```
   DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```
4. Run the DB schema: `source .venv/bin/activate && python tools/db_init.py`
5. Verify tables created: `python tools/db_verify.py`

**Why blocked:** All DB tools (`db_init.py`, `ingest_fastf1.py`, `save_markets.py`, `ingest_historical.py`) skip gracefully without `DATABASE_URL` but cannot actually write data.

---

## BLOCKER 2: Vercel deployment (Required to go public)

**What's needed:**
1. Go to https://vercel.com and import the GitHub repo `joethefisher/f1-oracle`
2. Set the **Root Directory** to `web` in Vercel project settings
3. Add these environment variables in Vercel dashboard:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://[project-ref].supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-anon-key]
   ```
   Both are found in Supabase → Project Settings → API
4. Deploy — Vercel will auto-detect Next.js and build correctly

**Why blocked:** Vercel deployment requires your GitHub account auth and environment variable values I don't have.

---

## BLOCKER 3: Historical data ingestion (Required before model can be trained)

Once Supabase is connected (Blocker 1 resolved), run this in the terminal:

```bash
source .venv/bin/activate

# Ingest 2022-2024 race results (takes ~30 min due to FastF1 download)
python tools/ingest_historical.py --seasons 2022 2023 2024 --session R

# Ingest qualifying results for same seasons
python tools/ingest_historical.py --seasons 2022 2023 2024 --session Q
```

**Why blocked:** FastF1 downloads large data files. Running this takes 20-40 minutes and requires active DB connection. Once done, tell me and I'll wire up the model training step.

---

## BLOCKER 4: Model training (After Blocker 3)

Once historical data is ingested, I need to write `tools/build_training_data.py` that:
1. Queries `race_results` + `qualifying_results` from DB
2. Calls `build_race_features()` for each historical race
3. Constructs training labels (won=1/0 per race winner per driver)
4. Calls `train_market_model()` and saves models to `.tmp/models/`

This is a 1-hour build task I can do as soon as you tell me the data is in the DB.

---

## BLOCKER 5: Live Kalshi market prices in frontend (Tab 1)

Tab 1 currently shows mock data. To show live Oracle vs Kalshi:
1. After Supabase is set up, I'll add a Supabase query in `/web/app/race/page.tsx`
2. The query reads `predictions` joined to `markets` for the active race
3. Kalshi live prices need a periodic refresh — I recommend a cron job running `tools/snapshot_orderbook.py` before each race and storing prices in a `price_snapshots` table

This is ready to build as soon as Blockers 1–3 are resolved.

---

## BLOCKER 6: Make GitHub repo public (Phase 6)

The repo at https://github.com/joethefisher/f1-oracle is currently **private**.

To make it public:
1. Go to the repo on GitHub
2. Settings → Danger Zone → Change repository visibility → Make public

Wait until you've done a few shadow-mode race weekends (Phase 5) before going public.

---

## Summary: What's done vs blocked

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Foundation | ✅ Complete | DB schema, FastF1 ingestion, Kalshi market tools |
| Phase 2 — Prediction Model | ✅ Complete | Feature engineering, LogReg, backtest — needs data to train |
| Phase 3 — Portfolio Engine | ✅ Complete | Half-Kelly bets, settlement, portfolio snapshots |
| Phase 4 — Frontend | ✅ Complete | 3-tab site builds, dark theme, mock data wired |
| Phase 5 — Shadow Mode | 🔒 Blocked | Needs Supabase (B1) + historical data (B3) + model training (B4) |
| Phase 6 — Launch | 🔒 Blocked | Needs Vercel deploy (B2) + public repo (B6) |

**80 Python tests passing. Next.js build passing.**
