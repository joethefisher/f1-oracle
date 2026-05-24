"""Tests for the notification formatters (tools/summaries.py)."""
from tools.summaries import format_bets_placed, format_results, format_portfolio


def test_bets_placed_lists_each_bet_and_total():
    bets = [
        {"market_type": "race_winner", "driver": "NOR", "oracle_prob": 0.217,
         "kalshi_mid": 0.11, "edge": 0.107, "bet_size": 71.15},
        {"market_type": "podium", "driver": "PIA", "oracle_prob": 0.506,
         "kalshi_mid": 0.40, "edge": 0.106, "bet_size": 31.49},
    ]
    msg = format_bets_placed("Canadian Grand Prix", bets, bankroll=1058.0)
    assert "Canadian Grand Prix" in msg
    assert "NOR" in msg and "PIA" in msg
    assert "102.64" in msg  # total staked
    assert "2 bets" in msg


def test_bets_placed_empty():
    msg = format_bets_placed("Canadian Grand Prix", [], bankroll=1000.0)
    assert "no bets" in msg.lower()


def test_results_shows_winner_record_and_net():
    bet_results = [
        {"market_type": "podium", "driver": "PIA", "won": True, "pnl": 45.20, "bet_size": 31.49},
        {"market_type": "race_winner", "driver": "NOR", "won": False, "pnl": -71.15, "bet_size": 71.15},
    ]
    msg = format_results("Canadian Grand Prix", "RUS", bet_results)
    assert "Winner: RUS" in msg
    assert "✅" in msg and "❌" in msg
    assert "1/2 won" in msg
    assert "-25.95" in msg  # net


def test_results_no_bets():
    msg = format_results("Canadian Grand Prix", "RUS", [])
    assert "No bets" in msg


def test_portfolio_ahead_of_baseline():
    snap = {"bankroll_after": 1058.0, "return_pct": 5.8, "kalshi_baseline_value": 1020.0}
    msg = format_portfolio(snap)
    assert "1058" in msg
    assert "+5.80% season" in msg
    assert "ahead of" in msg
    assert "38.00" in msg  # 1058 - 1020


def test_portfolio_behind_baseline():
    snap = {"bankroll_after": 980.0, "return_pct": -2.0, "kalshi_baseline_value": 1010.0}
    msg = format_portfolio(snap)
    assert "behind" in msg


def test_portfolio_without_baseline():
    snap = {"bankroll_after": 1000.0, "return_pct": 0.0, "kalshi_baseline_value": None}
    msg = format_portfolio(snap)
    assert "Bankroll" in msg
    assert "baseline" not in msg.lower()
