"""Tests for output validation (tools/validate.py)."""
from tools.validate import validate_distribution, validate_prices


def test_valid_winner_distribution_passes():
    assert validate_distribution("race_winner", [0.5, 0.3, 0.2], target_sum=1.0) == []


def test_valid_podium_distribution_passes():
    # Sums to 3 — the correct podium target.
    assert validate_distribution("podium", [0.9, 0.8, 0.7, 0.6], target_sum=3.0) == []


def test_podium_normalized_to_one_is_caught():
    # The exact regression: podium probs summing to 1 instead of 3.
    probs = [0.4, 0.3, 0.2, 0.1]  # sums to 1.0
    problems = validate_distribution("podium", probs, target_sum=3.0)
    assert any("sum" in p for p in problems)


def test_nan_probability_is_caught():
    problems = validate_distribution("race_winner", [float("nan"), 0.5, 0.5], target_sum=1.0)
    assert any("NaN" in p for p in problems)


def test_out_of_range_probability_is_caught():
    problems = validate_distribution("race_winner", [1.4, -0.4], target_sum=1.0)
    assert any("outside (0, 1]" in p for p in problems)


def test_empty_predictions_is_caught():
    assert validate_distribution("pole", [], target_sum=1.0) == ["pole: no predictions produced"]


def test_validate_prices_flags_missing_and_degenerate():
    problems = validate_prices("race_winner", [0.3, None, 0.0, 1.0, 0.5])
    assert len(problems) == 3  # None, 0.0, 1.0 are all bad; 0.3 and 0.5 are fine
