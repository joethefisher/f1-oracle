"""
Static driver-to-constructor mapping for 2022–2026.
Used by the Elo engine to compute constructor pace ratings from qualifying sessions.

Missing entries default to STARTING_ELO (1500) in elo.py — no crash, just a neutral rating.
"""

TEAM_ROSTERS: dict[tuple[int, str], str] = {
    # ── 2022 ──────────────────────────────────────────────────────────────────
    (2022, "VER"): "Red Bull",    (2022, "PER"): "Red Bull",
    (2022, "LEC"): "Ferrari",     (2022, "SAI"): "Ferrari",
    (2022, "HAM"): "Mercedes",    (2022, "RUS"): "Mercedes",
    (2022, "ALO"): "Alpine",      (2022, "OCO"): "Alpine",
    (2022, "NOR"): "McLaren",     (2022, "RIC"): "McLaren",
    (2022, "BOT"): "Alfa Romeo",  (2022, "ZHO"): "Alfa Romeo",
    (2022, "VET"): "Aston Martin",(2022, "STR"): "Aston Martin",
    (2022, "LAT"): "Williams",    (2022, "ALB"): "Williams",
    (2022, "GAS"): "AlphaTauri",  (2022, "TSU"): "AlphaTauri",
    (2022, "MAG"): "Haas",        (2022, "MSC"): "Haas",
    # ── 2023 ──────────────────────────────────────────────────────────────────
    (2023, "VER"): "Red Bull",    (2023, "PER"): "Red Bull",
    (2023, "LEC"): "Ferrari",     (2023, "SAI"): "Ferrari",
    (2023, "HAM"): "Mercedes",    (2023, "RUS"): "Mercedes",
    (2023, "ALO"): "Aston Martin",(2023, "STR"): "Aston Martin",
    (2023, "GAS"): "Alpine",      (2023, "OCO"): "Alpine",
    (2023, "NOR"): "McLaren",     (2023, "PIA"): "McLaren",
    (2023, "BOT"): "Alfa Romeo",  (2023, "ZHO"): "Alfa Romeo",
    (2023, "ALB"): "Williams",    (2023, "SAR"): "Williams",
    (2023, "DEV"): "AlphaTauri",  (2023, "TSU"): "AlphaTauri",
    (2023, "RIC"): "AlphaTauri",  # de Vries replaced mid-season
    (2023, "MAG"): "Haas",        (2023, "HUL"): "Haas",
    # ── 2024 ──────────────────────────────────────────────────────────────────
    (2024, "VER"): "Red Bull",    (2024, "PER"): "Red Bull",
    (2024, "LEC"): "Ferrari",     (2024, "SAI"): "Ferrari",
    (2024, "HAM"): "Mercedes",    (2024, "RUS"): "Mercedes",
    (2024, "ALO"): "Aston Martin",(2024, "STR"): "Aston Martin",
    (2024, "GAS"): "Alpine",      (2024, "OCO"): "Alpine",
    (2024, "DOO"): "Alpine",      # Doohan replaced Ocon late 2024
    (2024, "NOR"): "McLaren",     (2024, "PIA"): "McLaren",
    (2024, "BOT"): "Kick Sauber", (2024, "ZHO"): "Kick Sauber",
    (2024, "ALB"): "Williams",    (2024, "SAR"): "Williams",
    (2024, "COL"): "Williams",    # Colapinto replaced Sargeant late 2024
    (2024, "TSU"): "RB",          (2024, "RIC"): "RB",
    (2024, "LAW"): "RB",          # Lawson replaced Ricciardo mid-season
    (2024, "MAG"): "Haas",        (2024, "HUL"): "Haas",
    # ── 2025 ──────────────────────────────────────────────────────────────────
    (2025, "VER"): "Red Bull",    (2025, "LAW"): "Red Bull",
    (2025, "LEC"): "Ferrari",     (2025, "HAM"): "Ferrari",
    (2025, "RUS"): "Mercedes",    (2025, "ANT"): "Mercedes",
    (2025, "ALO"): "Aston Martin",(2025, "STR"): "Aston Martin",
    (2025, "GAS"): "Alpine",      (2025, "DOO"): "Alpine",
    (2025, "COL"): "Alpine",      # if Colapinto raced mid-2025
    (2025, "NOR"): "McLaren",     (2025, "PIA"): "McLaren",
    (2025, "HUL"): "Kick Sauber", (2025, "BOR"): "Kick Sauber",
    (2025, "ALB"): "Williams",    (2025, "SAI"): "Williams",
    (2025, "TSU"): "RB",          (2025, "HAD"): "RB",
    (2025, "OCO"): "Haas",        (2025, "BEA"): "Haas",
    # ── 2026 ──────────────────────────────────────────────────────────────────
    (2026, "VER"): "Red Bull",    (2026, "TSU"): "Red Bull",
    (2026, "LEC"): "Ferrari",     (2026, "HAM"): "Ferrari",
    (2026, "RUS"): "Mercedes",    (2026, "ANT"): "Mercedes",
    (2026, "ALO"): "Aston Martin",(2026, "STR"): "Aston Martin",
    (2026, "GAS"): "Alpine",      (2026, "DOO"): "Alpine",
    (2026, "COL"): "Alpine",
    (2026, "NOR"): "McLaren",     (2026, "PIA"): "McLaren",
    (2026, "HUL"): "Kick Sauber", (2026, "BOR"): "Kick Sauber",
    (2026, "ALB"): "Williams",    (2026, "SAI"): "Williams",
    (2026, "LAW"): "RB",          (2026, "HAD"): "RB",
    (2026, "OCO"): "Haas",        (2026, "BEA"): "Haas",
}


def get_constructor(season: int, abbreviation: str) -> str | None:
    return TEAM_ROSTERS.get((season, abbreviation))
