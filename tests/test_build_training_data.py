import pandas as pd
import numpy as np
import pytest

from tools.build_training_data import build_training_df, MARKET_TYPES


def _make_race_results(n_races: int = 5, n_drivers: int = 10) -> pd.DataFrame:
    rows = []
    for season in [2022]:
        for round_num in range(1, n_races + 1):
            for drv_idx in range(n_drivers):
                rows.append({
                    "race_id": (season - 2022) * 30 + round_num,
                    "season": season,
                    "round": round_num,
                    "circuit": f"circuit_{round_num % 3}",
                    "abbreviation": f"D{drv_idx:02d}",
                    "position": drv_idx + 1,
                    "grid_position": (drv_idx + 2) % n_drivers + 1,
                })
    return pd.DataFrame(rows)


def _make_quali_results(n_races: int = 5, n_drivers: int = 10) -> pd.DataFrame:
    rows = []
    for round_num in range(1, n_races + 1):
        for drv_idx in range(n_drivers):
            rows.append({
                "race_id": round_num,
                "season": 2022,
                "round": round_num,
                "circuit": f"circuit_{round_num % 3}",
                "abbreviation": f"D{drv_idx:02d}",
                "quali_position": drv_idx + 1,
            })
    return pd.DataFrame(rows)


def test_build_training_df_returns_dataframe():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    assert isinstance(df, pd.DataFrame)


def test_build_training_df_skips_first_race():
    """First race has no prior history so it must be excluded."""
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    # round 1 has no prior data — should not appear
    assert 1 not in df["race_id"].unique()


def test_build_training_df_includes_later_races():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    assert len(df) > 0


def test_build_training_df_has_target_columns():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    for col in ["won", "podium", "pole"]:
        assert col in df.columns


def test_build_training_df_won_is_binary():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    assert set(df["won"].unique()).issubset({0, 1})


def test_build_training_df_podium_is_binary():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    assert set(df["podium"].unique()).issubset({0, 1})


def test_build_training_df_pole_is_binary():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    assert set(df["pole"].unique()).issubset({0, 1})


def test_build_training_df_one_winner_per_race():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    wins_per_race = df.groupby("race_id")["won"].sum()
    assert (wins_per_race == 1).all()


def test_build_training_df_three_podium_per_race():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    podiums_per_race = df.groupby("race_id")["podium"].sum()
    assert (podiums_per_race == 3).all()


def test_build_training_df_one_pole_per_race():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    poles_per_race = df.groupby("race_id")["pole"].sum()
    assert (poles_per_race == 1).all()


def test_build_training_df_empty_when_no_prior():
    """Only 1 race — no prior data, should produce empty dataframe."""
    race = _make_race_results(1, 10)
    quali = _make_quali_results(1, 10)
    df = build_training_df(race, quali)
    assert df.empty


def test_build_training_df_fallback_to_race_grid_without_quali():
    """Without qualifying data, falls back to race grid_position."""
    race = _make_race_results(5, 10)
    empty_quali = pd.DataFrame(
        columns=["race_id", "season", "round", "circuit", "abbreviation", "quali_position"]
    )
    df = build_training_df(race, empty_quali)
    assert isinstance(df, pd.DataFrame)
    # pole column should be all zeros since no quali
    if not df.empty:
        assert (df["pole"] == 0).all()


def test_build_training_df_has_feature_columns():
    from tools.train_model import FEATURE_COLS
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    for col in FEATURE_COLS:
        assert col in df.columns, f"Missing feature column: {col}"


def test_build_training_df_has_race_id_column():
    race = _make_race_results(5, 10)
    quali = _make_quali_results(5, 10)
    df = build_training_df(race, quali)
    assert "race_id" in df.columns


def test_market_types_list():
    assert "race_winner" in MARKET_TYPES
    assert "podium" in MARKET_TYPES
    assert "pole" in MARKET_TYPES
