def test_get_rounds_for_season_2024():
    from tools.ingest_historical import get_rounds_for_season
    rounds = get_rounds_for_season(2024)
    assert len(rounds) == 24


def test_get_rounds_for_season_2023():
    from tools.ingest_historical import get_rounds_for_season
    rounds = get_rounds_for_season(2023)
    assert len(rounds) == 22


def test_rounds_include_sprint_flag():
    from tools.ingest_historical import get_rounds_for_season
    rounds = get_rounds_for_season(2024)
    assert "round_num" in rounds[0]
    assert "has_sprint" in rounds[0]
    assert isinstance(rounds[0]["has_sprint"], bool)
