"""Tests for the notification formatters (tools/summaries.py)."""
from tools.summaries import (
    format_bets_placed, format_results, format_portfolio, format_weekend_review,
)


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


# ── format_weekend_review ────────────────────────────────────────────────────

def _row(driver, oracle, market, bet=0.0, won=False, pos=None, fav=False, pnl=0.0):
    return {"driver": driver, "oracle": oracle, "market_mid": market,
            "bet_size": bet, "won": won, "position": pos, "is_favorite": fav,
            "pnl": pnl, "edge": (oracle - market) if (oracle is not None and market is not None) else None}


def test_weekend_review_headlines_faded_favorite_that_hit():
    # ANT was a favorite the model rated below market (faded), and it won.
    weekend = {
        "race_name": "Canadian Grand Prix",
        "bet_time": None,
        "by_market": {
            "race_winner": [
                _row("ANT", 0.21, 0.325, fav=True, won=True, pos=1),
                _row("RUS", 0.30, 0.425, fav=True, won=False, pos=None),
                _row("NOR", 0.22, 0.11,  bet=71.15, won=False, pos=None, pnl=-71.15),
            ],
        },
    }
    msg = format_weekend_review(weekend)
    assert "Canadian Grand Prix" in msg
    assert "1/1" not in msg  # NOR lost
    assert "0/1 won" in msg or "0/1" in msg  # one bet, lost
    assert "faded favorite(s) hit" in msg
    assert "ANT" in msg and "P1" in msg


def test_weekend_review_silent_when_no_faded_hit():
    weekend = {
        "race_name": "Spanish GP", "bet_time": None,
        "by_market": {"race_winner": [
            _row("X", 0.10, 0.40, fav=True, won=False, pos=5),  # faded fav, missed
            _row("Y", 0.15, 0.10, bet=20.0, won=True, pos=1, pnl=170.0),
        ]},
    }
    msg = format_weekend_review(weekend)
    assert "faded favorite(s) hit" not in msg
    assert "value strategy held up" in msg
    assert "1/1" in msg  # 1 of 1 bet won


def test_weekend_review_no_bets_placed():
    weekend = {"race_name": "Monaco GP", "bet_time": None, "by_market": {}}
    msg = format_weekend_review(weekend)
    assert "No bets placed" in msg
