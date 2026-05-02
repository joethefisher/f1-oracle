from unittest.mock import patch, MagicMock


def test_is_wet_dry_below_threshold():
    from tools.fetch_weather import is_wet_from_precipitation
    assert is_wet_from_precipitation(0.0) is False
    assert is_wet_from_precipitation(0.9) is False


def test_is_wet_at_threshold():
    from tools.fetch_weather import is_wet_from_precipitation
    assert is_wet_from_precipitation(1.0) is True
    assert is_wet_from_precipitation(5.0) is True


def test_fetch_weather_returns_dry():
    from tools.fetch_weather import fetch_weather
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"daily": {"precipitation_sum": [0.0]}}
    mock_resp.raise_for_status = MagicMock()
    with patch("tools.fetch_weather.requests.get", return_value=mock_resp):
        result = fetch_weather(lat=25.958, lon=-80.239, date_str="2026-05-04")
    assert result["is_wet"] is False
    assert result["precipitation_mm"] == 0.0


def test_fetch_weather_returns_wet():
    from tools.fetch_weather import fetch_weather
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"daily": {"precipitation_sum": [12.5]}}
    mock_resp.raise_for_status = MagicMock()
    with patch("tools.fetch_weather.requests.get", return_value=mock_resp):
        result = fetch_weather(lat=25.958, lon=-80.239, date_str="2026-05-04")
    assert result["is_wet"] is True
    assert result["precipitation_mm"] == 12.5
