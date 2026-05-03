from datetime import date, timedelta
import requests

WET_THRESHOLD_MM = 1.0
_ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Archive has a ~5-day lag; use forecast for anything more recent
_ARCHIVE_LAG_DAYS = 5


def is_wet_from_precipitation(precipitation_mm: float) -> bool:
    return precipitation_mm >= WET_THRESHOLD_MM


def fetch_weather(lat: float, lon: float, date_str: str) -> dict:
    """
    Fetch precipitation for a given date and location.
    Automatically uses the forecast endpoint for dates within the last 5 days
    or in the future (archive API has a ~5-day lag).
    Returns {"is_wet": bool, "precipitation_mm": float}.
    """
    target = date.fromisoformat(date_str)
    cutoff = date.today() - timedelta(days=_ARCHIVE_LAG_DAYS)

    if target >= cutoff:
        # Forecast endpoint: supports past 92 days + 16-day forecast
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum",
            "start_date": date_str,
            "end_date": date_str,
            "timezone": "UTC",
            "forecast_days": 16,
        }
        resp = requests.get(_FORECAST_URL, params=params, timeout=10)
    else:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum",
            "start_date": date_str,
            "end_date": date_str,
            "timezone": "UTC",
        }
        resp = requests.get(_ARCHIVE_URL, params=params, timeout=10)

    resp.raise_for_status()
    data = resp.json()
    daily = data.get("daily", {})
    values = daily.get("precipitation_sum", [None])
    precipitation = float(values[0]) if values and values[0] is not None else 0.0
    return {"is_wet": is_wet_from_precipitation(precipitation), "precipitation_mm": precipitation}
