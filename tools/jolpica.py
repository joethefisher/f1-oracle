"""
Fetch F1 race and qualifying results from Jolpica (Ergast-compatible API).
Used as fallback when FastF1 lap data is unavailable (typically pre-2023).

Docs: https://api.jolpi.ca/ergast/
"""
import requests
from typing import Any

BASE = "https://api.jolpi.ca/ergast/f1"
TIMEOUT = 15


def _get(path: str) -> dict:
    resp = requests.get(f"{BASE}{path}.json?limit=30", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_race_results(season: int, round_num: int) -> list[dict[str, Any]]:
    """Returns list of {abbreviation, position, grid_position, driver_name, team_name, status, points}."""
    data = _get(f"/{season}/{round_num}/results")
    races = data["MRData"]["RaceTable"]["Races"]
    if not races:
        return []
    rows = []
    for r in races[0]["Results"]:
        rows.append({
            "abbreviation": r["Driver"]["code"],
            "driver_name": f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
            "driver_number": r["Driver"].get("permanentNumber", ""),
            "team_name": r["Constructor"]["name"],
            "position": int(r["position"]),
            "grid_position": int(r["grid"]) if r.get("grid") else None,
            "status": r.get("status", ""),
            "points": float(r.get("points", 0)),
        })
    return rows


def fetch_qualifying_results(season: int, round_num: int) -> list[dict[str, Any]]:
    """Returns list of {abbreviation, position, grid_position, driver_name, team_name}."""
    data = _get(f"/{season}/{round_num}/qualifying")
    races = data["MRData"]["RaceTable"]["Races"]
    if not races:
        return []
    rows = []
    for r in races[0]["QualifyingResults"]:
        pos = int(r["position"])
        rows.append({
            "abbreviation": r["Driver"]["code"],
            "driver_name": f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
            "driver_number": r["Driver"].get("permanentNumber", ""),
            "team_name": r["Constructor"]["name"],
            "position": pos,
            "grid_position": pos,
            "status": "",
            "points": None,
        })
    return rows
