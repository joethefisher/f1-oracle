"""Tests for correlation-aware joint Kelly sizing (tools/kelly_portfolio.py)."""
import numpy as np

from tools.kelly_portfolio import (
    simulate_ranks, candidate_outcomes, optimize_kelly, size_portfolio,
)
from tools.portfolio import half_kelly_bet_size


def test_simulate_ranks_marginal_matches_win_prob():
    # P(driver finishes first) should ~equal its strength share.
    strengths = {"A": 0.5, "B": 0.3, "C": 0.2}
    ranks = simulate_ranks(strengths, n=40000, rng=np.random.default_rng(0))
    p_first = {d: float((r == 0).mean()) for d, r in ranks.items()}
    assert abs(p_first["A"] - 0.5) < 0.02
    assert abs(p_first["B"] - 0.3) < 0.02
    assert abs(p_first["C"] - 0.2) < 0.02


def test_candidate_outcome_marginal_matches_oracle_prob():
    strengths = {"A": 0.5, "B": 0.3, "C": 0.2}
    rng = np.random.default_rng(1)
    ranks = simulate_ranks(strengths, n=40000, rng=rng)
    cands = [{"market_type": "podium", "driver": "B", "price": 0.5, "oracle_prob": 0.7}]
    outcomes = candidate_outcomes(ranks, cands, rng=rng)
    assert abs(outcomes[:, 0].mean() - 0.7) < 0.02  # marginal == oracle prob


def test_single_bet_matches_analytic_half_kelly():
    # One uncorrelated bet should reproduce the classic half-Kelly fraction.
    rng = np.random.default_rng(2)
    strengths = {"A": 0.4, "B": 0.3, "C": 0.3}
    q, price, bankroll = 0.40, 0.25, 1000.0
    cands = [{"market_type": "race_winner", "driver": "A", "price": price, "oracle_prob": q}]
    sized = size_portfolio(cands, strengths, bankroll, n=60000, rng=rng)
    analytic = half_kelly_bet_size(q, price, bankroll)
    assert abs(sized[0]["bet_size"] - analytic) < analytic * 0.15  # within MC noise


def test_no_edge_no_bet():
    strengths = {"A": 0.4, "B": 0.6}
    cands = [{"market_type": "race_winner", "driver": "A", "price": 0.40, "oracle_prob": 0.42}]
    sized = size_portfolio(cands, strengths, 1000.0, n=10000, rng=np.random.default_rng(3))
    assert sized[0]["bet_size"] == 0.0  # edge 2% < MIN_EDGE 5%


def test_missing_price_no_bet():
    strengths = {"A": 0.4, "B": 0.6}
    cands = [{"market_type": "race_winner", "driver": "A", "price": None, "oracle_prob": 0.9}]
    sized = size_portfolio(cands, strengths, 1000.0, n=10000, rng=np.random.default_rng(4))
    assert sized[0]["bet_size"] == 0.0


def test_total_stake_respects_cap():
    # Many strong edges — total stake must not exceed MAX_TOTAL_PCT of bankroll.
    strengths = {d: 1.0 for d in "ABCDEF"}
    cands = [
        {"market_type": "podium", "driver": d, "price": 0.20, "oracle_prob": 0.60}
        for d in "ABCDEF"
    ]
    bankroll = 1000.0
    sized = size_portfolio(cands, strengths, bankroll, n=20000, rng=np.random.default_rng(5))
    total = sum(s["bet_size"] for s in sized)
    assert total <= 0.50 * bankroll + 1e-6
    assert all(s["bet_size"] <= 0.10 * bankroll + 1e-6 for s in sized)


def test_perfectly_correlated_bets_not_double_staked():
    # Two identical bets (same driver/outcome) are perfectly correlated: only the
    # combined position matters, so joint Kelly stakes ~one position's worth —
    # far below the naive sum of two independent half-Kelly bets.
    rng = np.random.default_rng(6)
    strengths = {"A": 0.4, "B": 0.3, "C": 0.3}
    c = {"market_type": "race_winner", "driver": "A", "price": 0.30, "oracle_prob": 0.42}
    bankroll = 1000.0
    sized = size_portfolio([dict(c), dict(c)], strengths, bankroll, n=40000, rng=rng)
    joint_total = sum(s["bet_size"] for s in sized)
    independent_sum = 2 * half_kelly_bet_size(0.42, 0.30, bankroll)
    assert joint_total > 0
    assert joint_total < 0.75 * independent_sum  # not double-staked
