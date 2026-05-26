"""Truth-table tests for the favorites-faded review logic (tools/review_weekend.py)."""
from tools.review_weekend import classify_decision, is_faded_favorite, mark_favorites


# ── classify_decision ────────────────────────────────────────────────────────

def test_bet_taken():
    assert classify_decision(0.22, 0.11, 71.15) == "bet"


def test_no_price():
    assert classify_decision(0.30, None, 0.0) == "no price"
    assert classify_decision(0.30, 0.0, 0.0) == "no price"
    assert classify_decision(0.30, 1.0, 0.0) == "no price"


def test_no_model_prob():
    assert classify_decision(None, 0.11, 0.0) == "no model prob"


def test_faded_favorite_negative_edge():
    # Model rates a driver below the market → never a YES bet.
    assert classify_decision(0.209, 0.325, 0.0) == "faded (model below market)"


def test_positive_edge_below_floor():
    out = classify_decision(0.161, 0.110, 0.0, min_edge=0.05)
    assert out.startswith("edge +5.1% < 5%") is False  # 5.1 is above floor
    # use a sub-floor edge
    out2 = classify_decision(0.044, 0.0, 0.0)  # no price guard hits first
    assert out2 == "no price"
    out3 = classify_decision(0.235, 0.195, 0.0, min_edge=0.05)
    assert "4.0%" in out3 and "< 5%" in out3


def test_positive_edge_dropped_by_kelly():
    # Edge clears the floor but no stake was placed → joint Kelly dropped it.
    assert classify_decision(0.20, 0.10, 0.0, min_edge=0.05) == "+edge but dropped by joint Kelly"


# ── mark_favorites ───────────────────────────────────────────────────────────

def test_mark_favorites_tags_top_n_by_price():
    rows = [
        {"driver": "RUS", "market_mid": 0.425},
        {"driver": "ANT", "market_mid": 0.325},
        {"driver": "NOR", "market_mid": 0.110},
        {"driver": "PIA", "market_mid": 0.045},
    ]
    mark_favorites(rows, 2)
    favs = {r["driver"] for r in rows if r["is_favorite"]}
    assert favs == {"RUS", "ANT"}


def test_mark_favorites_excludes_unpriced():
    rows = [
        {"driver": "RUS", "market_mid": 0.42},
        {"driver": "X", "market_mid": None},
        {"driver": "Y", "market_mid": None},
    ]
    mark_favorites(rows, 3)
    assert rows[0]["is_favorite"] is True
    assert rows[1]["is_favorite"] is False and rows[2]["is_favorite"] is False


# ── is_faded_favorite ────────────────────────────────────────────────────────

def test_faded_favorite_true_when_below_market():
    assert is_faded_favorite({"is_favorite": True, "oracle": 0.21, "market_mid": 0.325}) is True


def test_not_faded_when_model_above_market():
    assert is_faded_favorite({"is_favorite": True, "oracle": 0.55, "market_mid": 0.40}) is False


def test_not_faded_when_not_favorite():
    assert is_faded_favorite({"is_favorite": False, "oracle": 0.10, "market_mid": 0.40}) is False


def test_not_faded_with_missing_data():
    assert is_faded_favorite({"is_favorite": True, "oracle": None, "market_mid": 0.40}) is False
    assert is_faded_favorite({"is_favorite": True, "oracle": 0.2, "market_mid": None}) is False
