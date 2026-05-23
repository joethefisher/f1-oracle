import pandas as pd
from tools.elo import STARTING_ELO


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


def make_qualifying_df():
    return pd.DataFrame([
        {"abbreviation": "NOR", "position": 1},
        {"abbreviation": "VER", "position": 2},
        {"abbreviation": "LEC", "position": 3},
    ])


def test_compute_circuit_history_filters_by_circuit():
    from tools.build_features import compute_circuit_history
    results = make_results_df()
    history = compute_circuit_history(results, circuit="Miami", current_season=2026, n_seasons=3)
    assert abs(history.loc["NOR", "circuit_history"] - 1.0) < 0.01
    assert abs(history.loc["LEC", "circuit_history"] - 2.0) < 0.01


def test_compute_circuit_history_returns_empty_for_no_history():
    from tools.build_features import compute_circuit_history
    results = make_results_df()
    history = compute_circuit_history(results, circuit="Singapore", current_season=2025, n_seasons=3)
    assert len(history) == 0


def test_build_race_features_returns_one_row_per_driver():
    from tools.build_features import build_race_features
    results = make_results_df()
    features = build_race_features(
        results_history=results,
        qualifying_df=make_qualifying_df(),
        circuit="Miami",
        current_round=4,
        current_season=2025,
        is_wet=False,
    )
    assert len(features) == 3
    assert set(features.columns) >= {
        "abbreviation", "grid_position", "grid_pos_norm",
        "driver_elo", "constructor_elo", "circuit_history",
        "is_street_circuit", "is_wet",
    }


def test_build_race_features_street_circuit_flag():
    from tools.build_features import build_race_features
    results = make_results_df()
    # Miami is in STREET_CIRCUITS
    features_miami = build_race_features(
        results_history=results, qualifying_df=make_qualifying_df(),
        circuit="Miami", current_round=4, current_season=2025,
    )
    assert features_miami["is_street_circuit"].iloc[0] == 1

    # Bahrain is not
    features_bahrain = build_race_features(
        results_history=results, qualifying_df=make_qualifying_df(),
        circuit="Bahrain", current_round=4, current_season=2025,
    )
    assert features_bahrain["is_street_circuit"].iloc[0] == 0


def test_build_race_features_grid_pos_norm():
    from tools.build_features import build_race_features
    results = make_results_df()
    features = build_race_features(
        results_history=results, qualifying_df=make_qualifying_df(),
        circuit="Miami", current_round=4, current_season=2025,
    )
    # Pole sitter (position 1) should have grid_pos_norm = 0.0
    pole = features[features["abbreviation"] == "NOR"].iloc[0]
    assert abs(pole["grid_pos_norm"] - 0.0) < 1e-9
    # Last (position 3 of 3) should be 1.0
    last = features[features["abbreviation"] == "LEC"].iloc[0]
    assert abs(last["grid_pos_norm"] - 1.0) < 1e-9


def test_build_race_features_elo_defaults_to_starting():
    from tools.build_features import build_race_features
    results = make_results_df()
    features = build_race_features(
        results_history=results, qualifying_df=make_qualifying_df(),
        circuit="Miami", current_round=4, current_season=2025,
        driver_elo_snapshot=None, constructor_elo_snapshot=None,
    )
    assert (features["driver_elo"] == STARTING_ELO).all()
    assert (features["constructor_elo"] == STARTING_ELO).all()


def test_build_race_features_fills_missing_circuit_history():
    from tools.build_features import build_race_features
    results = make_results_df()
    features = build_race_features(
        results_history=results, qualifying_df=make_qualifying_df(),
        circuit="Singapore", current_round=4, current_season=2025,
    )
    assert len(features) == 3
    assert not features["circuit_history"].isna().any()


def test_build_prequali_features_has_no_grid():
    from tools.build_features import build_prequali_features
    results = make_results_df()
    feats = build_prequali_features(
        results_history=results,
        drivers=["NOR", "VER", "LEC"],
        circuit="Miami",
        current_season=2026,
    )
    cols = set(feats.columns)
    assert "grid_pos_norm" not in cols  # pole is predicted before qualifying
    assert "grid_position" not in cols
    for col in ["driver_elo", "constructor_elo", "circuit_history", "is_street_circuit", "is_wet"]:
        assert col in cols, f"missing {col}"
    assert len(feats) == 3


def test_build_prequali_features_dedups_drivers():
    from tools.build_features import build_prequali_features
    feats = build_prequali_features(
        results_history=make_results_df(),
        drivers=["NOR", "NOR", "VER"],
        circuit="Miami",
        current_season=2026,
    )
    assert len(feats) == 2


def test_build_prequali_features_empty_drivers():
    from tools.build_features import build_prequali_features
    feats = build_prequali_features(
        results_history=make_results_df(), drivers=[], circuit="Miami", current_season=2026,
    )
    assert feats.empty


def test_street_circuit_flag_in_prequali():
    from tools.build_features import build_prequali_features
    feats = build_prequali_features(
        results_history=make_results_df(), drivers=["NOR"], circuit="Monaco", current_season=2026,
    )
    assert feats["is_street_circuit"].iloc[0] == 1
