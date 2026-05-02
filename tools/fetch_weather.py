import requests

WET_THRESHOLD_MM = 1.0
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def is_wet_from_precipitation(precipitation_mm: float) -> bool:
    return precipitation_mm >= WET_THRESHOLD_MM


def fetch_weather(lat: float, lon: float, date_str: str) -> dict:
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
    precipitation = data["daily"]["precipitation_sum"][0] or 0.0
    return {"is_wet": is_wet_from_precipitation(precipitation), "precipitation_mm": precipitation}
