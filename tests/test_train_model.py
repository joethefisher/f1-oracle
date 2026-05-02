import numpy as np
import tempfile
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
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
    assert isinstance(model, Pipeline)
    assert hasattr(model.named_steps["clf"], "coef_")


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
    assert isinstance(model, Pipeline)


def test_train_market_model_podium():
    from tools.train_model import train_market_model
    df = make_df()
    model = train_market_model(df, "podium")
    assert isinstance(model, Pipeline)


def test_feature_cols_contains_expected():
    from tools.train_model import FEATURE_COLS
    for col in ["grid_position", "recent_form", "circuit_history", "quali_to_finish_delta", "is_wet"]:
        assert col in FEATURE_COLS
