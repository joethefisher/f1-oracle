"""Tests for calibration metrics computation (tools/eval_model.py)."""
from unittest.mock import patch

from tools.eval_model import brier_score, log_loss, compute_metrics, _actual_outcome


def test_brier_score_perfect():
    assert brier_score([1.0, 0.0], [1, 0]) == 0.0


def test_brier_score_known_value():
    # (0.7-1)^2 + (0.2-0)^2 = 0.09 + 0.04 = 0.13; /2 = 0.065
    assert abs(brier_score([0.7, 0.2], [1, 0]) - 0.065) < 1e-9


def test_actual_outcome_podium():
    race = {"VER": 2, "NOR": 5}
    assert _actual_outcome("podium", "VER", race, {}) == 1
    assert _actual_outcome("podium", "NOR", race, {}) == 0


def test_actual_outcome_pole_uses_quali():
    assert _actual_outcome("pole", "RUS", {}, {"RUS": 1}) == 1
    assert _actual_outcome("pole", "VER", {}, {"RUS": 1, "VER": 2}) == 0


def test_compute_metrics_structure_and_split():
    # Synthetic: 2 race_winner + 2 podium rows. Oracle better than Kalshi.
    race = (259, "Test GP")
    oracle = [0.9, 0.1, 0.8, 0.2]
    kalshi = [0.5, 0.5, 0.5, 0.5]
    actuals = [1, 0, 1, 0]
    mtypes = ["race_winner", "race_winner", "podium", "podium"]
    with patch("tools.eval_model._load_eval_rows", return_value=(race, oracle, kalshi, actuals, mtypes)):
        m = compute_metrics(259)
    assert set(m["by_market"]) == {"race_winner", "podium"}
    assert m["overall"]["n"] == 4
    assert m["by_market"]["race_winner"]["n"] == 2
    # Oracle is sharper than the 0.5 baseline -> lower Brier.
    assert m["overall"]["oracle_brier"] < m["overall"]["kalshi_brier"]


def test_compute_metrics_empty_when_no_rows():
    with patch("tools.eval_model._load_eval_rows", return_value=((259, "x"), [], [], [], [])):
        assert compute_metrics(259) == {}
