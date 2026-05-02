# F1 Oracle — Blockers Requiring User Action

Items that cannot be completed autonomously. Work through these in order.

---

## BLOCKER 1: Vercel deployment ✅ READY TO DEPLOY

**What's needed:**
1. Go to https://vercel.com → New Project
2. Import from GitHub: `joethefisher/f1-oracle`
3. Set **Root Directory** to `web`
4. Add these environment variables in Vercel dashboard (both from Supabase → Settings → API):
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://goexgkwgaahdnolskmok.supabase.co
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<your publishable key>
   ```
5. Click Deploy — auto-detects Next.js, builds from `web/`

**Current state:** Next.js builds cleanly. Pages show empty states until predictions exist (expected).
See `workflows/06_deploy_vercel.md` for full details.

---

## BLOCKER 2: Wait for model training (In progress)

Historical data ingestion is running now. Once complete (~30-40 min from start):
```bash
source .venv/bin/activate

# Train all models (race_winner, podium, pole)
python -m tools.build_training_data

# Verify models saved
ls -lh .tmp/models/
```

**Current state:** Race results for 2022-2024 being ingested. Qualifying results will run after. Model training script (`tools/build_training_data.py`) is written and tested.

---

## BLOCKER 3: Kalshi market setup before first live race weekend

Before the first race weekend prediction run, you'll need Kalshi event tickers for the race. These look like `KXF1RACE-MIAGP26` (Miami 2026). To find them:
```bash
source .venv/bin/activate
python -m tools.explore_markets --search "F1"
```

Then:
```bash
# Save markets for the race
python -m tools.save_markets --race-id <ID> --event <TICKER> --type race_winner
python -m tools.save_markets --race-id <ID> --event <TICKER> --type podium
python -m tools.save_markets --race-id <ID> --event <TICKER> --type pole
```

See `workflows/05_race_weekend.md` for the full race weekend cycle.

---

## BLOCKER 4: Make GitHub repo public (Phase 6 — shadow mode first)

The repo at https://github.com/joethefisher/f1-oracle is currently **private**.
Go public after 2-3 shadow mode race weekends to validate predictions look reasonable.

---

## Summary: What's done vs what's next

| Item | Status |
|------|--------|
| DB schema + Supabase | ✅ Connected |
| Race results 2022-2024 | 🔄 Ingesting (in progress) |
| Qualifying results 2022-2024 | 🔄 Queued after race results |
| Model training script | ✅ Written + tested |
| Frontend (3 tabs, live Supabase queries) | ✅ Complete |
| Vercel config | ✅ Ready — needs your deploy |
| Race weekend workflow | ✅ Documented |
| Shadow mode (first predictions) | ⏳ After model training + Kalshi markets |
| Launch | ⏳ After 2-3 shadow weekends |

**102 Python tests passing. TypeScript build clean.**
