"""
Train Oracle prediction models (one per market type).

Usage:
    python tools/train_model.py --market-type race_winner
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    "grid_pos_norm",
    "driver_elo",
    "constructor_elo",
    "circuit_history",
    "is_street_circuit",
    "is_wet",
]

MODEL_VERSION = "v2"

_TARGET_COL = {
    "race_winner": "won",
    "podium": "podium",
    "pole": "pole",
    "sprint": "sprint",
}

MODEL_DIR = Path(__file__).parent.parent / "models"


def train(X: np.ndarray, y: np.ndarray) -> CalibratedClassifierCV:
    base = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    model.fit(X, y)
    return model


def save_model(model: CalibratedClassifierCV, market_type: str, model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / f"{market_type}.joblib")


def load_model(market_type: str, model_dir: Path = MODEL_DIR) -> CalibratedClassifierCV:
    path = model_dir / f"{market_type}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No saved model for {market_type} at {path}")
    return joblib.load(path)


def train_market_model(df: pd.DataFrame, market_type: str) -> CalibratedClassifierCV:
    target = _TARGET_COL[market_type]
    X = df[FEATURE_COLS].values.astype(float)
    y = df[target].values
    return train(X, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-type", required=True, choices=list(_TARGET_COL))
    args = parser.parse_args()
    print(f"Training {args.market_type} model requires historical data in DB. Run build_training_data first.")


if __name__ == "__main__":
    main()
