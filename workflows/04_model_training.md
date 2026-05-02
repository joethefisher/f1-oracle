# Workflow 04: Model Training

## Objective
Train Oracle prediction models from historical F1 data stored in Supabase.

## Prerequisites
- Historical race results ingested (Workflow 03 complete for R sessions)
- Historical qualifying results ingested (Workflow 03 complete for Q sessions)
- `.venv` active with `scikit-learn` and `joblib` installed

## Steps

### 1. Verify data in DB
```bash
python -c "
from tools.db import cursor
with cursor() as cur:
    cur.execute('SELECT season, COUNT(*) FROM races GROUP BY season ORDER BY season')
    print('Races:', cur.fetchall())
    cur.execute('SELECT COUNT(*) FROM race_results WHERE position IS NOT NULL')
    print('Race result rows:', cur.fetchone())
    cur.execute('SELECT COUNT(*) FROM qualifying_results WHERE position IS NOT NULL')
    print('Qualifying rows:', cur.fetchone())
"
```

Expect: 2022 (22), 2023 (22), 2024 (24) races. At least 1,000 race result rows. Qualifying rows will be lower during initial ingestion.

### 2. Train all models
```bash
python -m tools.build_training_data
```

Output: `.tmp/models/race_winner.joblib`, `.tmp/models/podium.joblib`, `.tmp/models/pole.joblib`

### 3. Verify models saved
```bash
ls -lh .tmp/models/
```

### 4. (Optional) Re-train single market type
```bash
python -m tools.build_training_data --market-type race_winner
```

## Edge Cases
- **No qualifying data**: Falls back to race grid_position from race_results. Pole target will be all zeros. Models still train but pole accuracy will be lower until qualifying data is ingested.
- **Too few training rows**: If fewer than 20 prior rows exist for a race, it's excluded. Expect first 1-2 races per season to be skipped.
- **Model directory**: `.tmp/models/` is gitignored. Re-train after any `git clean` or fresh clone.

## Re-training Schedule
- Re-train after each completed season (all results settled)
- Optionally re-train mid-season after round 10+ if model performance is drifting
