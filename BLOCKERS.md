# F1 Oracle — Action Items

**Today is 2026-05-02. Miami GP 2026 is TOMORROW (May 3).**

---

## IMMEDIATE: Shadow Mode — Miami GP 2026

### 1. Set up Vercel (30 min)
Required before the site can be viewed publicly.

1. Go to https://vercel.com → New Project
2. Import: `joethefisher/f1-oracle`
3. Root Directory: `web`
4. Add env vars (from Supabase → Settings → API):
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://goexgkwgaahdnolskmok.supabase.co
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<your publishable key>
   ```
5. Deploy

### 2. Find Kalshi event tickers for Miami GP
Run:
```bash
source .venv/bin/activate
python -m tools.explore_markets
```

Look for event tickers for Miami 2026 race winner, podium, pole markets.
They'll look like `KXF1RACE-MIAGP26`.

### 3. After qualifying Saturday: run first shadow mode prediction
```bash
source .venv/bin/activate

# Ingest qualifying results
python -m tools.ingest_fastf1 --season 2026 --round 4 --session Q

# Snapshot Kalshi prices
python -m tools.snapshot_orderbook --event KXF1RACE-MIAGP26
python -m tools.save_orderbook_to_db   # saves latest snapshot to DB

# Save market structure
python -m tools.save_markets --season 2026 --round 4 --event KXF1RACE-MIAGP26 --type race_winner
python -m tools.save_markets --season 2026 --round 4 --event KXF1RACEPODIUM-MIAGP26 --type podium
python -m tools.save_markets --season 2026 --round 4 --event KXF1POLE-MIAGP26 --type pole

# Run model + place virtual bets
python -m tools.run_model --season 2026 --round 4
```

### 4. After race Sunday: settle and update portfolio
```bash
python -m tools.ingest_fastf1 --season 2026 --round 4 --session R
python -m tools.settle_outcomes --season 2026 --round 4
python -m tools.update_portfolio --season 2026 --round 4
```

---

## ONCE QUALIFYING INGESTION COMPLETES: Retrain pole model

Qualifying ingestion is running now (ETA ~30 min). After:
```bash
source .venv/bin/activate
python -m tools.build_training_data --market-type pole
```

---

## Ongoing Blockers

| Item | Status | Action |
|------|--------|--------|
| Vercel deploy | ⚠️ Needs your GitHub auth | See step 1 above |
| Miami Kalshi tickers | ⚠️ Needs manual lookup | Run `explore_markets` |
| Pole model | 🔄 Waiting for quali data | Auto-trains after quali |
| Make repo public | ⏳ After 2-3 shadow weekends | GitHub Settings → Visibility |

---

## System State (as of 2026-05-02)

| Item | Status |
|------|--------|
| DB: Race results 2022-2024 | ✅ 1,336 rows, all with position |
| DB: Qualifying 2022-2024 | 🔄 Ingesting (~42/68 complete) |
| DB: 2025 season (24 races) | ✅ Loaded (all completed) |
| DB: 2026 season (22 races) | ✅ Loaded, Miami marked active |
| Models: race_winner + podium | ✅ Trained on 66 races |
| Models: pole | ⏳ Trains after qualifying data loads |
| Frontend (3 tabs) | ✅ Live Supabase queries, empty states |
| Vercel config | ✅ web/vercel.json ready |

**102 Python tests passing. TypeScript build clean.**
