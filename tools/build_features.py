import pandas as pd


def compute_recent_form(
    results: pd.DataFrame,
    current_round: int,
    current_season: int,
    n: int = 3,
) -> pd.DataFrame:
    prior = results[
        (results["season"] == current_season) & (results["round"] < current_round)
    ].copy()
    prior = prior.sort_values("round", ascending=False)
    recent = prior.groupby("abbreviation").head(n)
    return (
        recent.groupby("abbreviation")["position"]
        .mean()
        .rename("recent_form")
        .to_frame()
    )


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


def compute_quali_to_finish_delta(
    results: pd.DataFrame,
    current_round: int,
    current_season: int,
    n: int = 3,
) -> pd.DataFrame:
    prior = results[
        (results["season"] == current_season) & (results["round"] < current_round)
    ].copy()
    prior = prior.sort_values("round", ascending=False)
    prior["delta"] = prior["grid_position"] - prior["position"]
    recent = prior.groupby("abbreviation").head(n)
    return (
        recent.groupby("abbreviation")["delta"]
        .mean()
        .rename("quali_to_finish_delta")
        .to_frame()
    )


def build_race_features(
    results_history: pd.DataFrame,
    qualifying_df: pd.DataFrame,
    circuit: str,
    current_round: int,
    current_season: int,
    is_wet: bool = False,
) -> pd.DataFrame:
    drivers = (
        qualifying_df[["abbreviation", "position"]]
        .rename(columns={"position": "grid_position"})
        .copy()
    )
    recent_form = compute_recent_form(results_history, current_round, current_season)
    circuit_hist = compute_circuit_history(results_history, circuit, current_season)
    delta = compute_quali_to_finish_delta(results_history, current_round, current_season)

    df = drivers.set_index("abbreviation")
    df = df.join(recent_form, how="left")
    df = df.join(circuit_hist, how="left")
    df = df.join(delta, how="left")

    median_grid = df["grid_position"].median()
    df = df.assign(
        circuit_history=df["circuit_history"].fillna(median_grid),
        recent_form=df["recent_form"].fillna(median_grid),
        quali_to_finish_delta=df["quali_to_finish_delta"].fillna(0.0),
        is_wet=int(is_wet),
    )
    return df.reset_index()
