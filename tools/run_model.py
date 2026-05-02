"""
Generate Oracle predictions for a race using trained models.

Usage:
    python tools/run_model.py --race-id 1 --market-type race_winner
"""
import argparse
import numpy as np
import pandas as pd
from rich.console import Console

from tools.train_model import FEATURE_COLS, load_model

console = Console()


def normalize_probabilities(raw_probs: np.ndarray) -> np.ndarray:
    total = raw_probs.sum()
    if total == 0:
        return np.ones_like(raw_probs) / len(raw_probs)
    return raw_probs / total


def predict_race(features_df: pd.DataFrame, model) -> list[dict]:
    X = features_df[FEATURE_COLS].values.astype(float)
    raw_probs = model.predict_proba(X)[:, 1]
    normalized = normalize_probabilities(raw_probs)
    results = [
        {"abbreviation": row["abbreviation"], "probability": round(float(p), 6)}
        for row, p in zip(features_df.to_dict("records"), normalized)
    ]
    return sorted(results, key=lambda x: x["probability"], reverse=True)


def save_predictions(race_id: int, market_id_map: dict, predictions: list[dict],
                     model_version: str, kalshi_mid_map: dict):
    from tools.db import cursor
    with cursor() as cur:
        for pred in predictions:
            abbrev = pred["abbreviation"]
            market_id = market_id_map.get(abbrev)
            if market_id is None:
                continue
            kalshi_mid = kalshi_mid_map.get(abbrev, 0.0)
            edge = round(pred["probability"] - kalshi_mid, 6)
            cur.execute("""
                INSERT INTO predictions
                    (market_id, oracle_probability, kalshi_mid_price, edge, model_version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (market_id, pred["probability"], kalshi_mid, edge, model_version))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-id", type=int, required=True)
    parser.add_argument("--market-type", required=True,
                        choices=["race_winner", "podium", "pole", "sprint"])
    parser.add_argument("--model-version", default="v1")
    args = parser.parse_args()
    model = load_model(args.market_type)
    console.print(f"[green]Loaded {args.market_type} model[/]")
    console.print("[yellow]Full pipeline requires DB + ingested data. See workflows/.[/]")


if __name__ == "__main__":
    main()
