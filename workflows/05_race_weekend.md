# Workflow 05: Race Weekend Prediction Cycle

## Objective
Generate Oracle predictions for an upcoming race weekend and log virtual bets.

## Prerequisites
- Models trained (Workflow 04 complete)
- Qualifying results available for the current race (session Q complete in FastF1)
- Kalshi markets open for this race
- `.env` has `DATABASE_URL` and `KALSHI_API_KEY_ID` (optional — public API works without auth for market prices)

## Race Weekend Timeline

### Friday / Saturday morning: snapshot Kalshi markets
```bash
python -m tools.save_markets --season 2025 --round 6
```

Saves markets from Kalshi to DB. Fetches mid prices for race_winner, podium, pole.

### After qualifying (Saturday evening): ingest qualifying results
```bash
python -m tools.ingest_fastf1 --season 2025 --round 6 --session Q
```

### After qualifying: run the model
```bash
python -m tools.run_model --season 2025 --round 6
```

This:
1. Builds features from qualifying grid positions + historical race data
2. Loads models from `.tmp/models/`
3. Generates probability estimates per driver per market
4. Saves predictions to `predictions` table
5. Saves virtual bets to `virtual_bets` table (half-Kelly sizing)

### After the race (Sunday evening): ingest race results
```bash
python -m tools.ingest_fastf1 --season 2025 --round 6 --session R
```

### Settle outcomes and update portfolio
```bash
python -m tools.settle_outcomes --season 2025 --round 6
python -m tools.update_portfolio --season 2025 --round 6
```

## Shadow Mode (first 2–3 weekends)
Run the full cycle but do not publish. Validate predictions look reasonable before going public.
Watch for: probabilities sum to ~1 per market, edge signs are plausible, no NaN/0 predictions.

## Edge Cases
- **Sprint weekend**: Also run `--session S` for sprint results after the sprint race.
- **Model not found**: Run `python -m tools.build_training_data` first.
- **Kalshi market not yet open**: Skip save_markets, run it again Friday once markets open.
- **FastF1 cache miss**: First load for a session fetches from network (~30s). Subsequent runs use cache.
