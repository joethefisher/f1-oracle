from tools.settle_outcomes import determine_winner, compute_pnl


def test_determine_winner_race_winner_p1():
    result = determine_winner(
        market_type="race_winner",
        driver_abbreviation="NOR",
        race_results={"NOR": 1, "VER": 2, "LEC": 3},
    )
    assert result is True


def test_determine_winner_race_winner_not_p1():
    result = determine_winner(
        market_type="race_winner",
        driver_abbreviation="VER",
        race_results={"NOR": 1, "VER": 2, "LEC": 3},
    )
    assert result is False


def test_determine_winner_podium_p3():
    result = determine_winner(
        market_type="podium",
        driver_abbreviation="LEC",
        race_results={"NOR": 1, "VER": 2, "LEC": 3},
    )
    assert result is True


def test_determine_winner_podium_p4():
    result = determine_winner(
        market_type="podium",
        driver_abbreviation="HAM",
        race_results={"NOR": 1, "VER": 2, "LEC": 3, "HAM": 4},
    )
    assert result is False


def test_determine_winner_pole_p1():
    result = determine_winner(
        market_type="pole",
        driver_abbreviation="NOR",
        race_results={"NOR": 1, "VER": 2},
    )
    assert result is True


def test_compute_pnl_win():
    pnl = compute_pnl(bet_size=50.0, kalshi_mid=0.38, won=True)
    expected = 50.0 * (1.0 / 0.38 - 1.0)
    assert abs(pnl - expected) < 0.01


def test_compute_pnl_loss():
    pnl = compute_pnl(bet_size=50.0, kalshi_mid=0.38, won=False)
    assert pnl == -50.0


def test_compute_pnl_no_bet():
    pnl = compute_pnl(bet_size=0.0, kalshi_mid=0.38, won=True)
    assert pnl == 0.0
