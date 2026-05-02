# Workflow: Weekly Learning Cycle

## Objective
Run the full post-race learning cycle every Monday after a race weekend. Update model parameters, calibration, strategy params, and lessons learned.

## Required Inputs
- Completed race weekend (results finalized)
- Race ID
- `ANTHROPIC_API_KEY` in `.env`

## Steps

### Step 1: Outcome Reconciliation
1. `tools/settle_outcomes.py --race {race_id}` — pulls final results from FastF1, settles all open positions
2. Computes realized PnL per bet and per cluster, writes to `outcomes` table

### Step 2: Model Retraining
1. `tools/retrain_model.py` — full retrain on all historical data including new race
2. Saves new model artifact to `models/race_winner_v{N}.pkl`
3. Logs training metrics (accuracy, log loss on held-out validation set)

### Step 3: Calibration Update
1. `tools/update_calibration.py --race {race_id}` — computes Brier score, reliability diagram for last race
2. Updates Platt scaling calibration function
3. Writes calibration metrics to `learning_records` table
4. **Brier score trend is the headline metric — print it clearly**

### Step 4: Strategy Parameter Analysis
1. `tools/analyze_strategy_params.py` — grid search over edge thresholds [3%,4%,5%,6%,7%], Kelly caps, max bets
2. Logs optimal parameters over time
3. Computes smoothed parameter update (do not abruptly shift — weight by recency)

### Step 5: Post-Mortem Agent (Claude API)
1. `tools/run_postmortem.py --race {race_id}` — loads bet log, outcomes, model predictions
2. Calls Claude API with structured prompts for each losing bet, each winning bet, each skipped edge
3. Parses structured output into `lessons` table
4. Budget cap: $20 per race weekend — estimate tokens before calling, truncate if needed

### Step 6: Lessons Escalation Check
1. `tools/check_recurring_lessons.py` — finds lessons seen 3+ times
2. Creates dashboard notification for human review (no approval gate, just visibility)

### Step 7: Feature Candidate A/B Evaluation
1. If any proposed features have accumulated enough data (3+ races): `tools/evaluate_feature_candidates.py`
2. Promotes winning candidates into live feature set for next retrain

## Expected Outputs
- Updated model artifact in `models/`
- New row in `learning_records` with Brier score, calibration, strategy params, lessons summary
- New rows in `lessons` for each post-mortem finding
- Console summary: Brier score (this race vs. season trend), net PnL, key lessons

## Notes
- Full retrain is cheap for the v1 model (<1 min). Keep it simple.
- Post-mortem agent costs ~$1-5/race. Log token usage each time.
- Never auto-change live parameters without logging the before/after values
