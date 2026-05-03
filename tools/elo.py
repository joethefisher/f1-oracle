"""
Elo rating engine for F1 Oracle model v2.

Two independent rating series:
  - Driver Elo: pairwise from race finishing positions (K=16)
  - Constructor Elo: pairwise from qualifying sessions, best car per team (K=8)

Both use 1500 as the starting rating and a 400-point scale (standard chess Elo).
Ratings are always computed as of BEFORE the target race to prevent data leakage.
"""

import pandas as pd

DRIVER_K = 16.0
CONSTRUCTOR_K = 8.0
STARTING_ELO = 1500.0


def _expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _pairwise_update(ratings: dict[str, float], ordered_ids: list[str], K: float) -> dict[str, float]:
    """
    Update ratings based on a single race/session result.

    ordered_ids: IDs sorted from best (P1) to worst.
    For every pair (winner, loser) where winner finished ahead: winner gains, loser loses.
    Returns a new ratings dict (does not mutate the input).
    """
    deltas: dict[str, float] = {id_: 0.0 for id_ in ordered_ids}
    for i, winner in enumerate(ordered_ids):
        r_win = ratings.get(winner, STARTING_ELO)
        for loser in ordered_ids[i + 1:]:
            r_los = ratings.get(loser, STARTING_ELO)
            exp_win = _expected(r_win, r_los)
            deltas[winner] += K * (1.0 - exp_win)
            deltas[loser] += K * (0.0 - (1.0 - exp_win))

    updated = dict(ratings)
    for id_, delta in deltas.items():
        updated[id_] = updated.get(id_, STARTING_ELO) + delta
    return updated


def _process_sessions(
    history: pd.DataFrame,
    ordered_id_col: str,
    K: float,
) -> dict[str, float]:
    """
    Process a sequence of sessions in chronological order and return final ratings.
    history must have columns: season, round, plus `ordered_id_col` and 'position'.
    """
    ratings: dict[str, float] = {}
    session_keys = (
        history[["season", "round"]]
        .drop_duplicates()
        .sort_values(["season", "round"])
        .values.tolist()
    )
    for season, round_num in session_keys:
        session = history[
            (history["season"] == season) & (history["round"] == round_num)
        ].dropna(subset=["position"]).sort_values("position")
        ordered = session[ordered_id_col].tolist()
        if ordered:
            ratings = _pairwise_update(ratings, ordered, K)
    return ratings


def get_driver_elo_snapshot(
    race_history: pd.DataFrame,
    season: int,
    round_num: int,
) -> dict[str, float]:
    """
    Returns {abbreviation: elo} representing driver skill going INTO (season, round_num).
    Uses all races strictly before that round.

    race_history columns: season, round, abbreviation, position
    """
    prior = race_history[
        (race_history["season"] < season)
        | ((race_history["season"] == season) & (race_history["round"] < round_num))
    ]
    return _process_sessions(prior, "abbreviation", DRIVER_K)


def get_constructor_elo_snapshot(
    quali_history: pd.DataFrame,
    season: int,
    round_num: int,
    team_rosters: dict[tuple[int, str], str],
) -> dict[str, float]:
    """
    Returns {constructor_name: elo} representing car pace going INTO (season, round_num).
    Uses all qualifying sessions strictly before that round.

    quali_history columns: season, round, abbreviation, position (= qualifying position)
    """
    prior = quali_history[
        (quali_history["season"] < season)
        | ((quali_history["season"] == season) & (quali_history["round"] < round_num))
    ].copy()

    if prior.empty:
        return {}

    prior["constructor"] = prior.apply(
        lambda r: team_rosters.get((int(r["season"]), r["abbreviation"])), axis=1
    )
    prior = prior.dropna(subset=["constructor", "position"])

    # Collapse each team to their best qualifying position per session
    best = (
        prior.groupby(["season", "round", "constructor"])["position"]
        .min()
        .reset_index()
        .rename(columns={"position": "position"})
    )
    best = best.rename(columns={"constructor": "abbreviation"})

    return _process_sessions(best, "abbreviation", CONSTRUCTOR_K)
