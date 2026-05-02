from tools.update_portfolio import (
    apply_settled_bets,
    compute_return_pct,
    compute_kalshi_baseline_pnl,
)


def test_apply_settled_bets_win():
    # bankroll=1000, win $50 at 0.38 → profit = 81.58
    bets = [{"bet_size": 50.0, "kalshi_mid": 0.38, "won": True}]
    new_bankroll = apply_settled_bets(1000.0, bets)
    expected = 1000.0 + 50.0 * (1.0 / 0.38 - 1.0)
    assert abs(new_bankroll - expected) < 0.01


def test_apply_settled_bets_loss():
    bets = [{"bet_size": 60.0, "kalshi_mid": 0.40, "won": False}]
    new_bankroll = apply_settled_bets(1000.0, bets)
    assert abs(new_bankroll - 940.0) < 0.01


def test_apply_settled_bets_mixed():
    bets = [
        {"bet_size": 50.0, "kalshi_mid": 0.38, "won": True},
        {"bet_size": 60.0, "kalshi_mid": 0.40, "won": False},
    ]
    new_bankroll = apply_settled_bets(1000.0, bets)
    expected = 1000.0 + 50.0 * (1.0 / 0.38 - 1.0) - 60.0
    assert abs(new_bankroll - expected) < 0.01


def test_apply_settled_bets_no_bets():
    new_bankroll = apply_settled_bets(1000.0, [])
    assert new_bankroll == 1000.0


def test_compute_return_pct():
    pct = compute_return_pct(starting=1000.0, current=1150.0)
    assert abs(pct - 15.0) < 0.001


def test_compute_return_pct_negative():
    pct = compute_return_pct(starting=1000.0, current=900.0)
    assert abs(pct - (-10.0)) < 0.001


def test_compute_kalshi_baseline_pnl_win():
    # Spread 100 over 2 bets: 60/40 by kalshi_mid. Both win.
    bets = [
        {"kalshi_mid": 0.60, "won": True},
        {"kalshi_mid": 0.40, "won": True},
    ]
    pnl = compute_kalshi_baseline_pnl(bets, oracle_total_bet=100.0)
    # 60% of 100 = 60 at 0.60 wins: +60*(1/0.60-1)=+40
    # 40% of 100 = 40 at 0.40 wins: +40*(1/0.40-1)=+60
    expected = 40.0 + 60.0
    assert abs(pnl - expected) < 0.01


def test_compute_kalshi_baseline_pnl_mixed():
    bets = [
        {"kalshi_mid": 0.60, "won": True},
        {"kalshi_mid": 0.40, "won": False},
    ]
    pnl = compute_kalshi_baseline_pnl(bets, oracle_total_bet=100.0)
    # 60 wins: +40; 40 loses: -40; net: 0
    assert abs(pnl - 0.0) < 0.01


def test_compute_kalshi_baseline_pnl_zero_outlay():
    bets = [{"kalshi_mid": 0.50, "won": True}]
    pnl = compute_kalshi_baseline_pnl(bets, oracle_total_bet=0.0)
    assert pnl == 0.0
