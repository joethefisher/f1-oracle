import pandas as pd

from tools.elo import STARTING_ELO

# Circuits where overtaking is severely limited and grid position is stickier.
# Street circuits have different grid→finish dynamics vs. permanent tracks.
STREET_CIRCUITS = {
    "Melbourne",   # Albert Park — tight, semi-street
    "Jeddah",
    "Baku",
    "Miami",
    "Monaco",
    "Singapore",
    "Las Vegas",
}


def compute_circuit_history(
    results: pd.DataFrame,
    circuit: str,
    current_season: int,
    n_seasons: int = 3,
) -> pd.DataFrame:
    hist = results[
        (results["circuit"] == circuit) & (results["season"] < current_season)
    ]
    recent_seasons = sorted(hist["season"].unique(), reverse=True)[:n_seasons]
    hist = hist[hist["season"].isin(recent_seasons)]
    if hist.empty:
        return pd.DataFrame(columns=["circuit_history"])
    return (
        hist.groupby("abbreviation")["position"]
        .mean()
        .rename("circuit_history")
        .to_frame()
    )


def build_race_features(
    results_history: pd.DataFrame,
    qualifying_df: pd.DataFrame,
    circuit: str,
    current_round: int,
    current_season: int,
    is_wet: bool = False,
    driver_elo_snapshot: dict[str, float] | None = None,
    constructor_elo_snapshot: dict[str, float] | None = None,
    team_rosters: dict[tuple[int, str], str] | None = None,
) -> pd.DataFrame:
    """
    Build the v2 feature matrix for a single race.

    Features (v2):
      grid_pos_norm      - normalized qualifying position (0=pole, 1=last)
      driver_elo         - pairwise race Elo (driver skill + recent form)
      constructor_elo    - pairwise qualifying Elo (car pace)
      circuit_history    - avg finish position at this circuit, last 3 seasons
      is_street_circuit  - binary: circuit in STREET_CIRCUITS set
      is_wet             - binary: wet conditions flag
    """
    base = (
        qualifying_df[["abbreviation", "position"]]
        .copy()
        .rename(columns={"position": "grid_position"})
    )

    n_drivers = max(len(base), 1)

    # Driver Elo: skill going into this race
    if driver_elo_snapshot:
        d_elo = base["abbreviation"].map(lambda a: driver_elo_snapshot.get(a, STARTING_ELO))
    else:
        d_elo = STARTING_ELO

    # Constructor Elo: car pace going into this race
    if constructor_elo_snapshot and team_rosters:
        def _cons_elo(abbrev: str) -> float:
            constructor = team_rosters.get((current_season, abbrev))
            if constructor:
                return constructor_elo_snapshot.get(constructor, STARTING_ELO)
            return STARTING_ELO
        c_elo = base["abbreviation"].map(_cons_elo)
    else:
        c_elo = STARTING_ELO

    drivers = base.assign(
        grid_pos_norm=(base["grid_position"] - 1) / (n_drivers - 1),
        driver_elo=d_elo,
        constructor_elo=c_elo,
    )

    # Circuit history (prior-season avg finish at this circuit)
    circuit_hist = compute_circuit_history(results_history, circuit, current_season)
    df = drivers.set_index("abbreviation").join(circuit_hist, how="left")

    median_grid = df["grid_position"].median()
    df = df.assign(
        circuit_history=pd.to_numeric(df["circuit_history"], errors="coerce").fillna(median_grid),
        is_street_circuit=int(circuit in STREET_CIRCUITS),
        is_wet=int(is_wet),
    )

    return df.reset_index()
