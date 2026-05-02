# F1 Oracle — Action Items

**Today is 2026-05-02. Miami GP 2026 is TOMORROW (May 3).**

---

## ✅ DONE: Qualifying Complete — Shadow Mode Active

Qualifying results ingested. Oracle model has run. **3 virtual bets placed.**

| Market | Driver | Oracle | Kalshi | Edge | Bet? |
|--------|--------|--------|--------|------|------|
| Race Winner | ANT | 46.7% | 41.0% | +5.7% | ✅ |
| Pole | ANT | 66.3% | 35.0% | +31.3% | ✅ |
| Pole | VER | 23.6% | 7.0% | +16.6% | ✅ |

**Qualifying result: P1 Antonelli, P2 Verstappen, P3 Leclerc, P4 Norris**

---

## TOMORROW (Race Day, May 3): Post-Race Settlement

After the race finishes:
```bash
source .venv/bin/activate

# 1. Ingest race results
python -m tools.ingest_fastf1 --season 2026 --round 4 --session R

# 2. Snapshot final Kalshi prices
python -m tools.snapshot_orderbook --event KXF1RACE-MIAGP26
python -m tools.snapshot_orderbook --event KXF1RACEPODIUM-MIAGP26
python -m tools.snapshot_orderbook --event KXF1POLE-MIAGP26
python -m tools.save_orderbook_to_db  # saves latest

# 3. Settle outcomes + update portfolio
python -m tools.settle_outcomes --season 2026 --round 4
python -m tools.update_portfolio --season 2026 --round 4

# 4. Mark race completed
# (python -c "from tools.db import cursor; ...")
```

After settlement, the Portfolio tab on the website will show real P&L.

---

## STILL NEEDED: Vercel Deployment

### Set up Vercel (30 min)
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

---

## System State (as of 2026-05-02 ~9:45 PM UTC)

| Item | Status |
|------|--------|
| DB: Race results 2022-2025 | ✅ 1,703 rows |
| DB: Qualifying 2022-2025 | ✅ 1,811 rows |
| DB: 2026 Miami quali results | ✅ 22 drivers (ANT on pole) |
| DB: Markets (all 3 types) | ✅ 66 markets saved |
| DB: Orderbook snapshots | ✅ 198 rows (6 snapshots × 22 drivers × 3 markets) |
| DB: Predictions | ✅ 66 predictions |
| DB: Virtual bets | ✅ 3 bets placed |
| Models: race_winner + podium + pole | ✅ Trained on 90 races |
| Frontend (3 tabs) | ✅ Supabase RSC queries, renders predictions |
| Vercel config | ✅ web/vercel.json ready |
| Python tests | ✅ 108 passing |
| TypeScript build | ✅ Clean |

**Race predictions are LIVE in the DB. The website will show them once Vercel is deployed.**
