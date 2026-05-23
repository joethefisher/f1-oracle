import numpy as np
import tempfile
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV
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
                "grid_pos_norm": driver / (n_drivers - 1),
                "driver_elo": rng.uniform(1400, 1600),
                "constructor_elo": rng.uniform(1400, 1600),
                "circuit_history": rng.uniform(1, 15),
                "is_street_circuit": int(race % 4 == 0),
                "is_wet": int(race % 5 == 0),
                "won": int(driver == 0),
                "podium": int(driver < 3),
                "pole": int(driver == 0),
            })
    return pd.DataFrame(rows)


def test_train_returns_fitted_model():
    from tools.train_model import train, FEATURE_COLS
    df = make_df()
    X = df[FEATURE_COLS].values
    y = df["won"].values
    model = train(X, y)
    assert isinstance(model, CalibratedClassifierCV)
    assert hasattr(model, "calibrated_classifiers_")


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
    assert isinstance(model, CalibratedClassifierCV)


def test_train_market_model_podium():
    from tools.train_model import train_market_model
    df = make_df()
    model = train_market_model(df, "podium")
    assert isinstance(model, CalibratedClassifierCV)


def test_feature_cols_contains_expected():
    from tools.train_model import FEATURE_COLS
    for col in ["grid_pos_norm", "driver_elo", "constructor_elo",
                "circuit_history", "is_street_circuit", "is_wet"]:
        assert col in FEATURE_COLS


def test_feature_cols_for_pole_excludes_grid():
    from tools.train_model import feature_cols_for, FEATURE_COLS, FEATURE_COLS_POLE
    assert "grid_pos_norm" not in feature_cols_for("pole")
    assert feature_cols_for("pole") == FEATURE_COLS_POLE
    assert "grid_pos_norm" in feature_cols_for("race_winner")
    assert feature_cols_for("race_winner") == FEATURE_COLS
    assert feature_cols_for("podium") == FEATURE_COLS
