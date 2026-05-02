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
    # current_season=2026 so 2025 Miami data is treated as prior history
    history = compute_circuit_history(results, circuit="Miami", current_season=2026, n_seasons=3)
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
