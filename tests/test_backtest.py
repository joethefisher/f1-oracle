import pandas as pd
from tools.backtest import compute_hit_rate, compute_virtual_pnl, BacktestResult


def test_hit_rate_all_correct():
    df = pd.DataFrame([
        {"bet_size": 10.0, "kalshi_mid": 0.5, "won": True},
        {"bet_size": 20.0, "kalshi_mid": 0.6, "won": True},
    ])
    assert compute_hit_rate(df) == 1.0


def test_hit_rate_all_wrong():
    df = pd.DataFrame([
        {"bet_size": 10.0, "kalshi_mid": 0.5, "won": False},
        {"bet_size": 20.0, "kalshi_mid": 0.6, "won": False},
    ])
    assert compute_hit_rate(df) == 0.0


def test_hit_rate_ignores_no_bet_rows():
    df = pd.DataFrame([
        {"bet_size": 10.0, "kalshi_mid": 0.5, "won": True},
        {"bet_size": 0.0,  "kalshi_mid": 0.4, "won": False},
    ])
    assert compute_hit_rate(df) == 1.0


def test_pnl_win_pays_correctly():
    df = pd.DataFrame([{"bet_size": 50.0, "kalshi_mid": 0.38, "won": True}])
    expected = 50.0 * (1.0 / 0.38 - 1.0)
    assert abs(compute_virtual_pnl(df) - expected) < 0.01


def test_pnl_loss_deducts_bet():
    df = pd.DataFrame([{"bet_size": 60.0, "kalshi_mid": 0.40, "won": False}])
    assert abs(compute_virtual_pnl(df) - (-60.0)) < 0.01


def test_pnl_mixed():
    df = pd.DataFrame([
        {"bet_size": 50.0, "kalshi_mid": 0.38, "won": True},
        {"bet_size": 60.0, "kalshi_mid": 0.40, "won": False},
        {"bet_size": 0.0,  "kalshi_mid": 0.35, "won": False},
    ])
    expected = 50.0 * (1.0 / 0.38 - 1.0) - 60.0
    assert abs(compute_virtual_pnl(df) - expected) < 0.01


def test_backtest_result_dataclass():
    r = BacktestResult(hit_rate=0.6, total_pnl=150.0, n_bets=10, n_wins=6)
    assert r.hit_rate == 0.6
    assert r.total_pnl == 150.0
