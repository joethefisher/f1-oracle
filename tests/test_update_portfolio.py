from tools.update_portfolio import (
    apply_settled_bets,
    compute_return_pct,
    compute_kalshi_baseline,
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


def test_compute_kalshi_baseline_same_total_outlay():
    # Baseline bets same total as Oracle, spread proportional to Kalshi prices
    markets = [
        {"kalshi_mid": 0.40, "oracle_bet": 50.0},
        {"kalshi_mid": 0.35, "oracle_bet": 0.0},   # Oracle didn't bet this one
        {"kalshi_mid": 0.25, "oracle_bet": 30.0},
    ]
    total_oracle = sum(m["oracle_bet"] for m in markets)  # 80
    result = compute_kalshi_baseline(markets, bankroll=1000.0, oracle_total_bet=total_oracle)
    # Baseline spreads 80 proportionally: 0.40/(0.40+0.35+0.25)*80 etc.
    assert len(result) == 3
    total_baseline = sum(r["bet_size"] for r in result)
    assert abs(total_baseline - total_oracle) < 0.01


def test_compute_kalshi_baseline_proportional():
    markets = [
        {"kalshi_mid": 0.60, "oracle_bet": 50.0},
        {"kalshi_mid": 0.40, "oracle_bet": 50.0},
    ]
    result = compute_kalshi_baseline(markets, bankroll=1000.0, oracle_total_bet=100.0)
    # 0.60 market gets 60% of 100 = 60, 0.40 gets 40
    assert abs(result[0]["bet_size"] - 60.0) < 0.01
    assert abs(result[1]["bet_size"] - 40.0) < 0.01
