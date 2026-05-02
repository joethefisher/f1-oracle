from tools.save_markets import build_market_rows


def test_build_market_rows_race_winner():
    markets = [
        {
            "ticker": "KXF1RACE-MIAGP26-NOR",
            "event_ticker": "KXF1RACE-MIAGP26",
            "yes_sub_title": "Lando Norris",
            "status": "open",
        },
        {
            "ticker": "KXF1RACE-MIAGP26-VER",
            "event_ticker": "KXF1RACE-MIAGP26",
            "yes_sub_title": "Max Verstappen",
            "status": "open",
        },
    ]
    rows = build_market_rows(markets, race_id=1, market_type="race_winner")
    assert len(rows) == 2
    assert rows[0]["kalshi_ticker"] == "KXF1RACE-MIAGP26-NOR"
    assert rows[0]["driver_name"] == "Lando Norris"
    assert rows[0]["market_type"] == "race_winner"
    assert rows[0]["race_id"] == 1


def test_build_market_rows_uses_title_when_no_sub_title():
    markets = [{
        "ticker": "KXF1POLE-MIAGP26-NOR",
        "event_ticker": "KXF1POLE-MIAGP26",
        "yes_sub_title": None,
        "title": "Lando Norris pole",
        "status": "open",
    }]
    rows = build_market_rows(markets, race_id=1, market_type="pole")
    assert rows[0]["driver_name"] == "Lando Norris pole"


def test_build_market_rows_empty_list():
    rows = build_market_rows([], race_id=1, market_type="race_winner")
    assert rows == []


def test_build_market_rows_preserves_status():
    markets = [{
        "ticker": "KXF1RACE-MIAGP26-NOR",
        "event_ticker": "KXF1RACE-MIAGP26",
        "yes_sub_title": "Lando Norris",
        "status": "closed",
    }]
    rows = build_market_rows(markets, race_id=2, market_type="race_winner")
    assert rows[0]["status"] == "closed"
