# Phase 2 — Prediction Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a feature engineering pipeline, logistic regression prediction model, and historical backtest for F1 race winner/podium/pole/sprint predictions.

**Architecture:** Feature engineering queries race_results and qualifying_results DataFrames to compute per-driver features (grid position, recent form, circuit history, quali-to-finish delta, weather). One LogisticRegression is trained per market type on historical data. Models are persisted with joblib. Prediction generation applies the model, normalizes probabilities to sum to 1, and writes to the predictions table.

**Tech Stack:** scikit-learn (LogisticRegression), joblib (model persistence), pandas (feature computation), Open-Meteo API (weather binary), FastF1 (historical ingestion)

---

## File Map

| File | Role |
|------|------|
| `tools/build_features.py` | Compute per-driver feature vectors from race/qualifying DataFrames |
| `tools/fetch_weather.py` | Fetch dry/wet binary from Open-Meteo API |
| `tools/train_model.py` | Train logistic regression per market type, save/load with joblib |
| `tools/run_model.py` | Generate predictions for a race, normalize, write to DB |
| `tools/ingest_historical.py` | Bulk ingest 2022–2025 FastF1 data into race/qualifying tables |
| `tools/backtest.py` | Evaluate model hit rate and virtual P&L on historical data |
| `tests/test_build_features.py` | Unit tests for feature engineering (pure pandas, no DB) |
| `tests/test_fetch_weather.py` | Unit tests for weather fetcher (mocked HTTP) |
| `tests/test_train_model.py` | Unit tests for training, save/load, normalization |
| `tests/test_run_model.py` | Unit tests for prediction generation |
| `tests/test_backtest.py` | Unit tests for hit rate and P&L computation |
| `tests/test_ingest_historical.py` | Unit tests for season round lookup |

---

### Task 1: Add scikit-learn and joblib to requirements

**Files:**
- Modify: `requirements.txt`
- Create: `tests/test_train_model.py` (import smoke test)

- [ ] **Step 1: Write the failing import test**

Create `tests/test_train_model.py`:
```python
def test_imports():
    import sklearn
    import joblib
    assert sklearn.__version__
    assert joblib.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_train_model.py::test_imports -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sklearn'`

- [ ] **Step 3: Update requirements and install**

Add to `requirements.txt`:
```
scikit-learn>=1.4.0
joblib>=1.4.0
```

Run: `source .venv/bin/activate && pip install "scikit-learn>=1.4.0" "joblib>=1.4.0"`

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest tests/test_train_model.py::test_imports -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/test_train_model.py
git commit -m "feat: add scikit-learn and joblib to requirements"
```

---

### Task 2: Feature engineering pipeline

**Files:**
- Create: `tools/build_features.py`
- Create: `tests/test_build_features.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_features.py`:
```python
import pandas as pd


def make_results_df():
    return pd.DataFrame([
        {"season": 2025, "round": 1, "circuit": "Bahrain", "abbreviation": "NOR", "position": 1, "grid_position": 1},
        {"season": 2025, "round": 1, "circuit": "Bahrain", "abbreviation": "VER", "position": 2, "grid_position": 2},
        {"season": 2025, "round": 1, "circuit": "Bahrain", "abbreviation": "LEC", "position": 3, "grid_position": 3},
        {"season": 2025, "round": 2, "circuit": "Jeddah",  "abbreviation": "VER", "position": 1, "grid_position": 1},
        {"season": 2025, "round": 2, "circuit": "Jeddah",  "abbreviation": "NOR", "position": 2, "grid_position": 3},
        {"season": 2025, "round": 2, "circuit": "Jeddah",  "abbreviation": "LEC", "position": 3, "grid_position": 2},
        {"season": 2025, "round": 3, "circuit": "Miami",   "abbreviation": "NOR", "position": 1, "grid_position": 1},
        {"season": 2025, "round": 3, "circuit": "Miami",   "abbreviation": "LEC", "position": 2, "grid_position": 2},
        {"season": 2025, "round": 3, "circuit": "Miami",   "abbreviation": "VER", "position": 3, "grid_position": 4},
    ])


def test_compute_recent_form_averages_last_n_races():
    from tools.build_features import compute_recent_form
    results = make_results_df()
    form = compute_recent_form(results, current_round=4, current_season=2025, n=3)
    assert abs(form.loc["NOR", "recent_form"] - (1 + 2 + 1) / 3) < 0.01
    assert abs(form.loc["VER", "recent_form"] - (2 + 1 + 3) / 3) < 0.01


def test_compute_recent_form_uses_at_most_n_races():
    from tools.build_features import compute_recent_form
    results = make_results_df()
    form = compute_recent_form(results, current_round=2, current_season=2025, n=3)
    assert abs(form.loc["NOR", "recent_form"] - 1.0) < 0.01


def test_compute_circuit_history_filters_by_circuit():
    from tools.build_features import compute_circuit_history
    results = make_results_df()
    history = compute_circuit_history(results, circuit="Miami", current_season=2025, n_seasons=3)
    assert abs(history.loc["NOR", "circuit_history"] - 1.0) < 0.01
    assert abs(history.loc["LEC", "circuit_history"] - 2.0) < 0.01


def test_compute_circuit_history_returns_empty_for_no_history():
    from tools.build_features import compute_circuit_history
    results = make_results_df()
    history = compute_circuit_history(results, circuit="Singapore", current_season=2025, n_seasons=3)
    assert len(history) == 0


def test_compute_quali_to_finish_delta_averages_gain():
    from tools.build_features import compute_quali_to_finish_delta
    results = make_results_df()
    # NOR: R1 grid=1 pos=1 delta=0, R2 grid=3 pos=2 delta=1, R3 grid=1 pos=1 delta=0 → avg=0.33
    delta = compute_quali_to_finish_delta(results, current_round=4, current_season=2025, n=3)
    assert abs(delta.loc["NOR", "quali_to_finish_delta"] - (0 + 1 + 0) / 3) < 0.01


def test_build_race_features_returns_one_row_per_driver():
    from tools.build_features import build_race_features
    results = make_results_df()
    qualifying_df = pd.DataFrame([
        {"abbreviation": "NOR", "position": 1},
        {"abbreviation": "VER", "position": 2},
        {"abbreviation": "LEC", "position": 3},
    ])
    features = build_race_features(
        results_history=results,
        qualifying_df=qualifying_df,
        circuit="Miami",
        current_round=4,
        current_season=2025,
        is_wet=False,
    )
    assert len(features) == 3
    assert set(features.columns) >= {"abbreviation", "grid_position", "recent_form",
                                      "circuit_history", "quali_to_finish_delta", "is_wet"}


def test_build_race_features_fills_missing_circuit_history():
    from tools.build_features import build_race_features
    results = make_results_df()
    qualifying_df = pd.DataFrame([
        {"abbreviation": "NOR", "position": 1},
        {"abbreviation": "VER", "position": 2},
        {"abbreviation": "LEC", "position": 3},
    ])
    features = build_race_features(
        results_history=results,
        qualifying_df=qualifying_df,
        circuit="Singapore",
        current_round=4,
        current_season=2025,
        is_wet=False,
    )
    assert len(features) == 3
    assert not features["circuit_history"].isna().any()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_build_features.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.build_features'`

- [ ] **Step 3: Write the implementation**

Create `tools/build_features.py`:
```python
import pandas as pd


def compute_recent_form(
    results: pd.DataFrame,
    current_round: int,
    current_season: int,
    n: int = 3,
) -> pd.DataFrame:
    prior = results[
        (results["season"] == current_season) & (results["round"] < current_round)
    ].copy()
    prior = prior.sort_values("round", ascending=False)
    recent = prior.groupby("abbreviation").head(n)
    return (
        recent.groupby("abbreviation")["position"]
        .mean()
        .rename("recent_form")
        .to_frame()
    )


def compute_circuit_history(
    results: pd.DataFrame,
    circuit: str,
    current_season: int,
    n_seasons: int = 3,
) -> pd.DataFrame:
    hist = results[
        (results["circuit"] == circuit) & (results["season"] < current_season)
    ]
    recent_seasons = sorted(hist["season"].unique(), reverse=True)[:n_seasons]
    hist = hist[hist["season"].isin(recent_seasons)]
    if hist.empty:
        return pd.DataFrame(columns=["circuit_history"])
    return (
        hist.groupby("abbreviation")["position"]
        .mean()
        .rename("circuit_history")
        .to_frame()
    )


def compute_quali_to_finish_delta(
    results: pd.DataFrame,
    current_round: int,
    current_season: int,
    n: int = 3,
) -> pd.DataFrame:
    prior = results[
        (results["season"] == current_season) & (results["round"] < current_round)
    ].copy()
    prior = prior.sort_values("round", ascending=False)
    prior["delta"] = prior["grid_position"] - prior["position"]
    recent = prior.groupby("abbreviation").head(n)
    return (
        recent.groupby("abbreviation")["delta"]
        .mean()
        .rename("quali_to_finish_delta")
        .to_frame()
    )


def build_race_features(
    results_history: pd.DataFrame,
    qualifying_df: pd.DataFrame,
    circuit: str,
    current_round: int,
    current_season: int,
    is_wet: bool = False,
) -> pd.DataFrame:
    drivers = (
        qualifying_df[["abbreviation", "position"]]
        .rename(columns={"position": "grid_position"})
        .copy()
    )
    recent_form = compute_recent_form(results_history, current_round, current_season)
    circuit_hist = compute_circuit_history(results_history, circuit, current_season)
    delta = compute_quali_to_finish_delta(results_history, current_round, current_season)

    df = drivers.set_index("abbreviation")
    df = df.join(recent_form, how="left")
    df = df.join(circuit_hist, how="left")
    df = df.join(delta, how="left")

    median_grid = df["grid_position"].median()
    df["circuit_history"] = df["circuit_history"].fillna(median_grid)
    df["recent_form"] = df["recent_form"].fillna(median_grid)
    df["quali_to_finish_delta"] = df["quali_to_finish_delta"].fillna(0.0)
    df["is_wet"] = int(is_wet)
    return df.reset_index()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_build_features.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/build_features.py tests/test_build_features.py
git commit -m "feat: add feature engineering pipeline for race predictions"
```

---

### Task 3: Weather fetcher

**Files:**
- Create: `tools/fetch_weather.py`
- Create: `tests/test_fetch_weather.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fetch_weather.py`:
```python
from unittest.mock import patch, MagicMock


def test_is_wet_dry_below_threshold():
    from tools.fetch_weather import is_wet_from_precipitation
    assert is_wet_from_precipitation(0.0) is False
    assert is_wet_from_precipitation(0.9) is False


def test_is_wet_at_threshold():
    from tools.fetch_weather import is_wet_from_precipitation
    assert is_wet_from_precipitation(1.0) is True
    assert is_wet_from_precipitation(5.0) is True


def test_fetch_weather_returns_dry():
    from tools.fetch_weather import fetch_weather
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"daily": {"precipitation_sum": [0.0]}}
    mock_resp.raise_for_status = MagicMock()
    with patch("tools.fetch_weather.requests.get", return_value=mock_resp):
        result = fetch_weather(lat=25.958, lon=-80.239, date_str="2026-05-04")
    assert result["is_wet"] is False
    assert result["precipitation_mm"] == 0.0


def test_fetch_weather_returns_wet():
    from tools.fetch_weather import fetch_weather
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"daily": {"precipitation_sum": [12.5]}}
    mock_resp.raise_for_status = MagicMock()
    with patch("tools.fetch_weather.requests.get", return_value=mock_resp):
        result = fetch_weather(lat=25.958, lon=-80.239, date_str="2026-05-04")
    assert result["is_wet"] is True
    assert result["precipitation_mm"] == 12.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_fetch_weather.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.fetch_weather'`

- [ ] **Step 3: Write the implementation**

Create `tools/fetch_weather.py`:
```python
import requests

WET_THRESHOLD_MM = 1.0
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def is_wet_from_precipitation(precipitation_mm: float) -> bool:
    return precipitation_mm >= WET_THRESHOLD_MM


def fetch_weather(lat: float, lon: float, date_str: str) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "start_date": date_str,
        "end_date": date_str,
        "timezone": "UTC",
    }
    resp = requests.get(_ARCHIVE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    precipitation = data["daily"]["precipitation_sum"][0] or 0.0
    return {"is_wet": is_wet_from_precipitation(precipitation), "precipitation_mm": precipitation}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_fetch_weather.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/fetch_weather.py tests/test_fetch_weather.py
git commit -m "feat: add Open-Meteo weather fetcher with wet/dry classification"
```

---

### Task 4: Model training

**Files:**
- Modify: `tests/test_train_model.py`
- Create: `tools/train_model.py`

- [ ] **Step 1: Replace tests/test_train_model.py with full test suite**

```python
import numpy as np
import tempfile
from pathlib import Path
from sklearn.linear_model import LogisticRegression
import pandas as pd


def test_imports():
    import sklearn, joblib
    assert sklearn.__version__
    assert joblib.__version__


def make_df(n_races=30, n_drivers=10):
    rng = np.random.default_rng(42)
    rows = []
    for race in range(n_races):
        for driver in range(n_drivers):
            rows.append({
                "grid_position": driver + 1,
                "recent_form": rng.uniform(1, 15),
                "circuit_history": rng.uniform(1, 15),
                "quali_to_finish_delta": rng.uniform(-3, 3),
                "is_wet": int(race % 5 == 0),
                "won": int(driver == 0),
                "podium": int(driver < 3),
            })
    return pd.DataFrame(rows)


def test_train_returns_fitted_model():
    from tools.train_model import train, FEATURE_COLS
    df = make_df()
    X = df[FEATURE_COLS].values
    y = df["won"].values
    model = train(X, y)
    assert isinstance(model, LogisticRegression)
    assert hasattr(model, "coef_")


def test_save_load_roundtrip():
    from tools.train_model import train, save_model, load_model, FEATURE_COLS
    df = make_df()
    X = df[FEATURE_COLS].values
    y = df["won"].values
    model = train(X, y)
    with tempfile.TemporaryDirectory() as tmpdir:
        save_model(model, "race_winner", Path(tmpdir))
        loaded = load_model("race_winner", Path(tmpdir))
    np.testing.assert_array_almost_equal(
        model.predict_proba(X[:5]),
        loaded.predict_proba(X[:5]),
    )


def test_train_market_model_race_winner():
    from tools.train_model import train_market_model
    df = make_df()
    model = train_market_model(df, "race_winner")
    assert isinstance(model, LogisticRegression)


def test_train_market_model_podium():
    from tools.train_model import train_market_model
    df = make_df()
    model = train_market_model(df, "podium")
    assert isinstance(model, LogisticRegression)


def test_feature_cols_contains_expected():
    from tools.train_model import FEATURE_COLS
    for col in ["grid_position", "recent_form", "circuit_history", "quali_to_finish_delta", "is_wet"]:
        assert col in FEATURE_COLS
```

- [ ] **Step 2: Run tests to verify they fail (except test_imports)**

Run: `source .venv/bin/activate && python -m pytest tests/test_train_model.py -v`
Expected: test_imports PASS, others FAIL with `ModuleNotFoundError: No module named 'tools.train_model'`

- [ ] **Step 3: Write the implementation**

Create `tools/train_model.py`:
```python
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
from sklearn.linear_model import LogisticRegression

FEATURE_COLS = ["grid_position", "recent_form", "circuit_history", "quali_to_finish_delta", "is_wet"]

_TARGET_COL = {
    "race_winner": "won",
    "podium": "podium",
    "pole": "pole",
    "sprint": "sprint",
}

MODEL_DIR = Path(__file__).parent.parent / ".tmp" / "models"


def train(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X, y)
    return model


def save_model(model: LogisticRegression, market_type: str, model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / f"{market_type}.joblib")


def load_model(market_type: str, model_dir: Path = MODEL_DIR) -> LogisticRegression:
    path = model_dir / f"{market_type}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No saved model for {market_type} at {path}")
    return joblib.load(path)


def train_market_model(df: pd.DataFrame, market_type: str) -> LogisticRegression:
    target = _TARGET_COL[market_type]
    X = df[FEATURE_COLS].values.astype(float)
    y = df[target].values
    return train(X, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-type", required=True, choices=list(_TARGET_COL))
    args = parser.parse_args()
    print(f"Training {args.market_type} model requires historical data in DB. Run ingest_historical.py first.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_train_model.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/train_model.py tests/test_train_model.py
git commit -m "feat: add model training with LogisticRegression, save/load with joblib"
```

---

### Task 5: Prediction generation

**Files:**
- Create: `tools/run_model.py`
- Create: `tests/test_run_model.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_run_model.py`:
```python
import numpy as np
import pandas as pd
from unittest.mock import MagicMock
from sklearn.linear_model import LogisticRegression


def make_mock_model(class1_probs):
    model = MagicMock(spec=LogisticRegression)
    p = np.array(class1_probs)
    model.predict_proba.return_value = np.column_stack([1 - p, p])
    return model


def make_features_df(abbreviations):
    n = len(abbreviations)
    return pd.DataFrame({
        "abbreviation": abbreviations,
        "grid_position": list(range(1, n + 1)),
        "recent_form": [3.0] * n,
        "circuit_history": [5.0] * n,
        "quali_to_finish_delta": [0.5] * n,
        "is_wet": [0] * n,
    })


def test_normalize_sums_to_one():
    from tools.run_model import normalize_probabilities
    normalized = normalize_probabilities(np.array([0.3, 0.1, 0.2]))
    assert abs(normalized.sum() - 1.0) < 1e-9


def test_normalize_preserves_order():
    from tools.run_model import normalize_probabilities
    normalized = normalize_probabilities(np.array([0.5, 0.3, 0.2]))
    assert normalized[0] > normalized[1] > normalized[2]


def test_predict_race_returns_list_of_dicts():
    from tools.run_model import predict_race
    features = make_features_df(["NOR", "VER", "LEC"])
    results = predict_race(features, make_mock_model([0.6, 0.3, 0.1]))
    assert isinstance(results, list)
    assert len(results) == 3
    assert "abbreviation" in results[0]
    assert "probability" in results[0]


def test_predict_race_probs_sum_to_one():
    from tools.run_model import predict_race
    features = make_features_df(["NOR", "VER", "LEC"])
    results = predict_race(features, make_mock_model([0.6, 0.3, 0.1]))
    assert abs(sum(r["probability"] for r in results) - 1.0) < 1e-6


def test_predict_race_sorted_descending():
    from tools.run_model import predict_race
    features = make_features_df(["NOR", "VER", "LEC"])
    results = predict_race(features, make_mock_model([0.6, 0.3, 0.1]))
    probs = [r["probability"] for r in results]
    assert probs == sorted(probs, reverse=True)


def test_predict_race_highest_prob_driver():
    from tools.run_model import predict_race
    features = make_features_df(["NOR", "VER", "LEC"])
    results = predict_race(features, make_mock_model([0.8, 0.15, 0.05]))
    assert results[0]["abbreviation"] == "NOR"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_run_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.run_model'`

- [ ] **Step 3: Write the implementation**

Create `tools/run_model.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_run_model.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/run_model.py tests/test_run_model.py
git commit -m "feat: add prediction generation with probability normalization"
```

---

### Task 6: Historical data ingestion

**Files:**
- Create: `tools/ingest_historical.py`
- Create: `tests/test_ingest_historical.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_historical.py`:
```python
def test_get_rounds_for_season_2024():
    from tools.ingest_historical import get_rounds_for_season
    rounds = get_rounds_for_season(2024)
    assert len(rounds) == 24


def test_get_rounds_for_season_2023():
    from tools.ingest_historical import get_rounds_for_season
    rounds = get_rounds_for_season(2023)
    assert len(rounds) == 22


def test_rounds_include_sprint_flag():
    from tools.ingest_historical import get_rounds_for_season
    rounds = get_rounds_for_season(2024)
    assert "round_num" in rounds[0]
    assert "has_sprint" in rounds[0]
    assert isinstance(rounds[0]["has_sprint"], bool)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_ingest_historical.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.ingest_historical'`

- [ ] **Step 3: Write the implementation**

Create `tools/ingest_historical.py`:
```python
"""
Bulk ingest FastF1 historical data for multiple seasons.

Usage:
    python tools/ingest_historical.py --seasons 2022 2023 2024
    python tools/ingest_historical.py --seasons 2022 2023 2024 --session Q
"""
import argparse
import time
from rich.console import Console

from tools.ingest_fastf1 import ingest

console = Console()

SEASON_ROUNDS = {2022: 22, 2023: 22, 2024: 24, 2025: 24}

SPRINT_ROUNDS = {
    (2022, 4), (2022, 11), (2022, 21),
    (2023, 4), (2023, 6), (2023, 12), (2023, 18), (2023, 20), (2023, 22),
    (2024, 5), (2024, 6), (2024, 11), (2024, 20), (2024, 21), (2024, 22),
    (2025, 1), (2025, 11), (2025, 14), (2025, 20), (2025, 21), (2025, 23),
}


def get_rounds_for_season(season: int) -> list[dict]:
    total = SEASON_ROUNDS.get(season, 24)
    return [
        {"round_num": r, "has_sprint": (season, r) in SPRINT_ROUNDS}
        for r in range(1, total + 1)
    ]


def ingest_season(season: int, session_type: str = "R", delay: float = 1.0):
    for entry in get_rounds_for_season(season):
        r = entry["round_num"]
        try:
            ingest(season, r, session_type)
            console.print(f"[green]✓ {season} R{r} ({session_type})[/]")
        except Exception as e:
            console.print(f"[yellow]✗ {season} R{r} ({session_type}): {e}[/]")
        time.sleep(delay)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", default=[2022, 2023, 2024])
    parser.add_argument("--session", default="R", choices=["R", "Q", "S"])
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    for season in args.seasons:
        ingest_season(season, args.session, args.delay)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_ingest_historical.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/ingest_historical.py tests/test_ingest_historical.py
git commit -m "feat: add bulk historical FastF1 ingestion tool"
```

---

### Task 7: Backtest engine

**Files:**
- Create: `tools/backtest.py`
- Create: `tests/test_backtest.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backtest.py`:
```python
import pandas as pd
from tools.backtest import compute_hit_rate, compute_virtual_pnl, BacktestResult


def test_hit_rate_all_correct():
    df = pd.DataFrame([
        {"bet_size": 10.0, "kalshi_mid": 0.5, "won": True},
        {"bet_size": 20.0, "kalshi_mid": 0.6, "won": True},
    ])
    assert compute_hit_rate(df) == 1.0


def test_hit_rate_all_wrong():
    df = pd.DataFrame([
        {"bet_size": 10.0, "kalshi_mid": 0.5, "won": False},
        {"bet_size": 20.0, "kalshi_mid": 0.6, "won": False},
    ])
    assert compute_hit_rate(df) == 0.0


def test_hit_rate_ignores_no_bet_rows():
    df = pd.DataFrame([
        {"bet_size": 10.0, "kalshi_mid": 0.5, "won": True},
        {"bet_size": 0.0,  "kalshi_mid": 0.4, "won": False},
    ])
    assert compute_hit_rate(df) == 1.0


def test_pnl_win_pays_correctly():
    # bet $50 at 0.38 → win profit = 50 * (1/0.38 - 1)
    df = pd.DataFrame([{"bet_size": 50.0, "kalshi_mid": 0.38, "won": True}])
    expected = 50.0 * (1.0 / 0.38 - 1.0)
    assert abs(compute_virtual_pnl(df) - expected) < 0.01


def test_pnl_loss_deducts_bet():
    df = pd.DataFrame([{"bet_size": 60.0, "kalshi_mid": 0.40, "won": False}])
    assert abs(compute_virtual_pnl(df) - (-60.0)) < 0.01


def test_pnl_mixed():
    df = pd.DataFrame([
        {"bet_size": 50.0, "kalshi_mid": 0.38, "won": True},
        {"bet_size": 60.0, "kalshi_mid": 0.40, "won": False},
        {"bet_size": 0.0,  "kalshi_mid": 0.35, "won": False},
    ])
    expected = 50.0 * (1.0 / 0.38 - 1.0) - 60.0
    assert abs(compute_virtual_pnl(df) - expected) < 0.01


def test_backtest_result_dataclass():
    r = BacktestResult(hit_rate=0.6, total_pnl=150.0, n_bets=10, n_wins=6)
    assert r.hit_rate == 0.6
    assert r.total_pnl == 150.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_backtest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.backtest'`

- [ ] **Step 3: Write the implementation**

Create `tools/backtest.py`:
```python
"""
Evaluate Oracle prediction accuracy and virtual P&L on historical data.

Usage:
    python tools/backtest.py --market-type race_winner
"""
import argparse
from dataclasses import dataclass
import pandas as pd
from rich.console import Console

console = Console()


@dataclass
class BacktestResult:
    hit_rate: float
    total_pnl: float
    n_bets: int
    n_wins: int


def compute_hit_rate(df: pd.DataFrame) -> float:
    bets = df[df["bet_size"] > 0]
    if len(bets) == 0:
        return 0.0
    return float(bets["won"].sum() / len(bets))


def compute_virtual_pnl(df: pd.DataFrame) -> float:
    total = 0.0
    for _, row in df.iterrows():
        if row["bet_size"] <= 0:
            continue
        if row["won"]:
            total += row["bet_size"] * (1.0 / row["kalshi_mid"] - 1.0)
        else:
            total -= row["bet_size"]
    return total


def run_backtest(df: pd.DataFrame) -> BacktestResult:
    bets = df[df["bet_size"] > 0]
    return BacktestResult(
        hit_rate=compute_hit_rate(df),
        total_pnl=round(compute_virtual_pnl(df), 2),
        n_bets=len(bets),
        n_wins=int(bets["won"].sum()),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-type", default="race_winner",
                        choices=["race_winner", "podium", "pole", "sprint"])
    args = parser.parse_args()
    console.print("[yellow]Backtest requires DATABASE_URL and historical data. Run ingest_historical.py first.[/]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_backtest.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Final Phase 2 test run + commit**

Run: `source .venv/bin/activate && python -m pytest --tb=short -q`
Expected: All tests pass

```bash
git add tools/backtest.py tests/test_backtest.py
git commit -m "feat: complete Phase 2 — feature engineering, model training, predictions, backtest"
git push
```
