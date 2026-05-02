"""
Query DB for historical race/qualifying results, build feature matrix, train and save models.

Usage:
    python -m tools.build_training_data
    python -m tools.build_training_data --market-type race_winner
"""
import argparse
from pathlib import Path

import pandas as pd
from rich.console import Console

from tools.db import cursor
from tools.build_features import build_race_features
from tools.train_model import train_market_model, save_model, MODEL_DIR

console = Console()

MARKET_TYPES = ["race_winner", "podium", "pole"]
MIN_PRIOR_ROWS = 20  # at least one full race grid worth of prior data


def load_all_race_results() -> pd.DataFrame:
    with cursor() as cur:
        cur.execute("""
            SELECT r.id AS race_id, r.season, r.round, r.circuit,
                   rr.abbreviation, rr.position, rr.grid_position
            FROM race_results rr
            JOIN races r ON rr.race_id = r.id
            WHERE rr.position IS NOT NULL
            ORDER BY r.season, r.round
        """)
        rows = cur.fetchall()
    return pd.DataFrame(
        rows,
        columns=["race_id", "season", "round", "circuit",
                 "abbreviation", "position", "grid_position"],
    )


def load_all_qualifying_results() -> pd.DataFrame:
    with cursor() as cur:
        cur.execute("""
            SELECT r.id AS race_id, r.season, r.round, r.circuit,
                   qr.abbreviation, qr.position AS quali_position
            FROM qualifying_results qr
            JOIN races r ON qr.race_id = r.id
            WHERE qr.position IS NOT NULL
            ORDER BY r.season, r.round
        """)
        rows = cur.fetchall()
    return pd.DataFrame(
        rows,
        columns=["race_id", "season", "round", "circuit", "abbreviation", "quali_position"],
    )


def build_training_df(
    race_results: pd.DataFrame,
    quali_results: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each race in the DB, build features using only prior races as history.
    Attaches targets: won, podium, pole.
    Skips a race if there is insufficient prior history.
    """
    all_rows: list[pd.DataFrame] = []

    race_keys = (
        race_results[["race_id", "season", "round", "circuit"]]
        .drop_duplicates()
        .sort_values(["season", "round"])
        .reset_index(drop=True)
    )

    for _, race in race_keys.iterrows():
        season = int(race["season"])
        round_num = int(race["round"])
        circuit = str(race["circuit"])
        race_id = int(race["race_id"])

        prior = race_results[
            (race_results["season"] < season)
            | ((race_results["season"] == season) & (race_results["round"] < round_num))
        ].copy()

        if len(prior) < MIN_PRIOR_ROWS:
            continue

        race_qual = quali_results[
            (quali_results["season"] == season) & (quali_results["round"] == round_num)
        ].copy()

        this_race = race_results[race_results["race_id"] == race_id].copy()

        if not race_qual.empty:
            grid_df = race_qual[["abbreviation", "quali_position"]].rename(
                columns={"quali_position": "position"}
            )
        else:
            grid_df = this_race[["abbreviation", "grid_position"]].rename(
                columns={"grid_position": "position"}
            )

        if grid_df.empty or grid_df["position"].isna().all():
            continue

        try:
            features = build_race_features(
                results_history=prior,
                qualifying_df=grid_df,
                circuit=circuit,
                current_round=round_num,
                current_season=season,
                is_wet=False,
            )
        except Exception:
            continue

        actuals = this_race[["abbreviation", "position"]].copy()
        actuals = actuals.assign(
            won=(actuals["position"] == 1).astype(int),
            podium=(actuals["position"] <= 3).astype(int),
        )

        if not race_qual.empty:
            pole_abbrevs = race_qual.loc[race_qual["quali_position"] == 1, "abbreviation"]
            actuals = actuals.assign(pole=actuals["abbreviation"].isin(pole_abbrevs).astype(int))
        else:
            actuals = actuals.assign(pole=0)

        merged = features.merge(
            actuals[["abbreviation", "won", "podium", "pole"]],
            on="abbreviation",
            how="inner",
        )
        merged["race_id"] = race_id
        all_rows.append(merged)

    if not all_rows:
        return pd.DataFrame()
    return pd.concat(all_rows, ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--market-type",
        choices=MARKET_TYPES,
        default=None,
        help="Train only this market type (default: all)",
    )
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    args = parser.parse_args()

    console.print("Loading historical data from DB...")
    race_results = load_all_race_results()
    quali_results = load_all_qualifying_results()

    if race_results.empty:
        console.print("[red]No race results in DB. Run ingest_historical.py first.[/]")
        return

    n_races = race_results["race_id"].nunique()
    console.print(
        f"Loaded {len(race_results)} driver-race rows across {n_races} races"
    )
    if not quali_results.empty:
        console.print(f"Loaded {len(quali_results)} qualifying rows")
    else:
        console.print("[yellow]No qualifying results in DB — using race grid positions as fallback[/]")

    console.print("Building feature matrix...")
    df = build_training_df(race_results, quali_results)

    if df.empty:
        console.print("[red]No training rows built. Check DB data.[/]")
        return

    n_training_races = df["race_id"].nunique()
    console.print(f"Training data: {len(df)} rows across {n_training_races} races")

    targets = [args.market_type] if args.market_type else MARKET_TYPES
    for market_type in targets:
        console.print(f"Training {market_type}...")
        model = train_market_model(df, market_type)
        save_model(model, market_type, args.model_dir)
        console.print(
            f"[green]✓ {market_type} saved → {args.model_dir}/{market_type}.joblib[/]"
        )

    console.print("[green]All models trained successfully.[/]")


if __name__ == "__main__":
    main()
