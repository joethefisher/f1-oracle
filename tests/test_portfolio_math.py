import pytest
from tools.portfolio import half_kelly_bet_size, kalshi_mid_price


def test_half_kelly_no_bet_below_min_edge():
    # Edge is 4% — below 5% threshold — should return 0
    result = half_kelly_bet_size(oracle_prob=0.32, kalshi_mid=0.28, bankroll=1000.0)
    assert result == 0.0


def test_half_kelly_bet_size_basic():
    # Oracle 35%, Kalshi 28% → edge 7%
    # kelly = 0.07 / (1 - 0.28) = 0.07 / 0.72 ≈ 0.09722
    # half_kelly = 0.04861
    # bet = 0.04861 * 1000 = $48.61
    result = half_kelly_bet_size(oracle_prob=0.35, kalshi_mid=0.28, bankroll=1000.0)
    assert abs(result - 48.61) < 0.1


def test_half_kelly_capped_at_10_pct_bankroll():
    # Very large edge should be capped at 10% of bankroll = $100
    result = half_kelly_bet_size(oracle_prob=0.90, kalshi_mid=0.10, bankroll=1000.0)
    assert result == 100.0


def test_half_kelly_zero_edge_exactly():
    result = half_kelly_bet_size(oracle_prob=0.28, kalshi_mid=0.28, bankroll=1000.0)
    assert result == 0.0


def test_half_kelly_negative_edge_returns_zero():
    # Oracle lower than Kalshi — no bet
    result = half_kelly_bet_size(oracle_prob=0.20, kalshi_mid=0.30, bankroll=1000.0)
    assert result == 0.0


def test_half_kelly_scales_with_bankroll():
    result_1k = half_kelly_bet_size(oracle_prob=0.35, kalshi_mid=0.28, bankroll=1000.0)
    result_2k = half_kelly_bet_size(oracle_prob=0.35, kalshi_mid=0.28, bankroll=2000.0)
    assert abs(result_2k - result_1k * 2) < 0.1


def test_half_kelly_no_price_returns_zero():
    # Missing price must never be treated as a 0 mid (which would read as a
    # full-probability edge and place a bet on a phantom price).
    assert half_kelly_bet_size(oracle_prob=0.52, kalshi_mid=None, bankroll=1000.0) == 0.0


def test_half_kelly_degenerate_price_returns_zero():
    assert half_kelly_bet_size(oracle_prob=0.52, kalshi_mid=0.0, bankroll=1000.0) == 0.0
    assert half_kelly_bet_size(oracle_prob=0.52, kalshi_mid=1.0, bankroll=1000.0) == 0.0


def test_kalshi_mid_price_both_sides():
    assert kalshi_mid_price(bid=0.25, ask=0.30) == 0.275


def test_kalshi_mid_price_ask_only():
    assert kalshi_mid_price(bid=None, ask=0.30) == 0.30


def test_kalshi_mid_price_bid_only():
    assert kalshi_mid_price(bid=0.25, ask=None) == 0.25


def test_kalshi_mid_price_neither_raises():
    with pytest.raises(ValueError, match="no price"):
        kalshi_mid_price(bid=None, ask=None)
