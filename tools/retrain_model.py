"""
Retrain all Oracle market models from current DB data.

Run after a race is settled so the next weekend's predictions reflect the latest
results. Training is deterministic (random_state=42), so the model artifacts only
change when new race data has landed — which is what makes the CI commit-back of
models/ bounded to post-race updates.

Usage:
    python -m tools.retrain_model
    python -m tools.retrain_model --market-type pole
"""
import argparse
import math
from pathlib import Path

from rich.console import Console

from tools.build_training_data import (
    load_all_race_results, load_all_qualifying_results, build_training_df, MARKET_TYPES,
)
from tools.train_model import (
    train_market_model, save_model, load_model, feature_cols_for, _TARGET_COL, MODEL_DIR,
)

console = Console()


def _in_sample_logloss(model, df, market_type) -> float:
    """Quick in-sample log loss as a training sanity signal (not a holdout score)."""
    import numpy as np
    X = df[feature_cols_for(market_type)].values.astype(float)
    y = df[_TARGET_COL[market_type]].values.astype(int)
    p = np.clip(model.predict_proba(X)[:, 1], 1e-7, 1 - 1e-7)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def retrain(market_types: list[str] | None = None, model_dir: Path = MODEL_DIR) -> dict:
    """Retrain the given market models (default all) from DB. Returns log-loss per market."""
    targets = market_types or MARKET_TYPES
    race_results = load_all_race_results()
    quali_results = load_all_qualifying_results()
    if race_results.empty:
        console.print("[red]No race results in DB — cannot retrain[/]")
        return {}

    df = build_training_df(race_results, quali_results)
    if df.empty:
        console.print("[red]No training rows built — cannot retrain[/]")
        return {}

    n_races = df["race_id"].nunique()
    console.print(f"Retraining on {len(df)} rows across {n_races} races")

    metrics = {}
    for market_type in targets:
        try:
            model = train_market_model(df, market_type)
        except ValueError as e:
            console.print(f"[yellow]Skipping {market_type}: {e}[/]")
            continue
        save_model(model, market_type, model_dir)
        ll = _in_sample_logloss(model, df, market_type)
        metrics[market_type] = ll
        console.print(f"[green]✓ {market_type} retrained (in-sample log loss {ll:.4f})[/]")
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Retrain Oracle models from DB")
    parser.add_argument("--market-type", choices=MARKET_TYPES, default=None)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    args = parser.parse_args()
    targets = [args.market_type] if args.market_type else None
    retrain(targets, args.model_dir)


if __name__ == "__main__":
    main()
