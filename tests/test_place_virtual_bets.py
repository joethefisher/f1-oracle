import pandas as pd
from tools.place_virtual_bets import compute_bets


def make_predictions():
    return [
        {"abbreviation": "NOR", "market_id": 1, "oracle_probability": 0.50, "kalshi_mid": 0.38},
        {"abbreviation": "VER", "market_id": 2, "oracle_probability": 0.30, "kalshi_mid": 0.35},  # edge < 5%
        {"abbreviation": "LEC", "market_id": 3, "oracle_probability": 0.20, "kalshi_mid": 0.10},  # edge = 10%
    ]


def test_compute_bets_returns_one_row_per_prediction():
    bets = compute_bets(make_predictions(), bankroll=1000.0)
    assert len(bets) == 3


def test_compute_bets_zero_for_insufficient_edge():
    bets = compute_bets(make_predictions(), bankroll=1000.0)
    ver_bet = next(b for b in bets if b["abbreviation"] == "VER")
    assert ver_bet["bet_size"] == 0.0


def test_compute_bets_nonzero_for_sufficient_edge():
    bets = compute_bets(make_predictions(), bankroll=1000.0)
    nor_bet = next(b for b in bets if b["abbreviation"] == "NOR")
    assert nor_bet["bet_size"] > 0.0


def test_compute_bets_respects_max_bet_pct():
    # Even with huge edge, bet capped at 10% of bankroll
    predictions = [{"abbreviation": "NOR", "market_id": 1, "oracle_probability": 0.99, "kalshi_mid": 0.01}]
    bets = compute_bets(predictions, bankroll=1000.0)
    assert bets[0]["bet_size"] <= 100.0  # 10% of 1000


def test_compute_bets_includes_kelly_fraction():
    bets = compute_bets(make_predictions(), bankroll=1000.0)
    nor_bet = next(b for b in bets if b["abbreviation"] == "NOR")
    assert "kelly_fraction" in nor_bet
    assert nor_bet["kelly_fraction"] > 0.0


def test_compute_bets_includes_bankroll():
    bets = compute_bets(make_predictions(), bankroll=1000.0)
    assert bets[0]["bankroll_at_time"] == 1000.0
