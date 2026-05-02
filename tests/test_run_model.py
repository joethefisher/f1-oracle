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
