"""
Generate Oracle predictions for a race using trained models and log virtual bets.

Usage:
    python -m tools.run_model --season 2025 --round 6
    python -m tools.run_model --season 2025 --round 6 --market-type race_winner
"""
import argparse
import numpy as np
import pandas as pd
from rich.console import Console

from tools.db import cursor
from tools.build_features import build_race_features
from tools.train_model import FEATURE_COLS, load_model
from tools.place_virtual_bets import compute_bets, save_bets
from tools.portfolio import MIN_EDGE

console = Console()

STARTING_BANKROLL = 1000.0
MARKET_TYPES = ["race_winner", "podium", "pole"]
MODEL_VERSION = "v1"


def normalize_probabilities(raw_probs: np.ndarray) -> np.ndarray:
    total = raw_probs.sum()
    if total == 0:
        return np.ones_like(raw_probs) / len(raw_probs)
    return raw_probs / total


def predict_race(features_df: pd.DataFrame, model) -> list[dict]:
    X = features_df[FEATURE_COLS].values.astype(float)
    raw_probs = model.predict_proba(X)[:, 1]
    normalized = normalize_probabilities(raw_probs)
    results = [
        {"abbreviation": row["abbreviation"], "probability": round(float(p), 6)}
        for row, p in zip(features_df.to_dict("records"), normalized)
    ]
    return sorted(results, key=lambda x: x["probability"], reverse=True)


def get_race_id(season: int, round_num: int) -> int:
    with cursor() as cur:
        cur.execute(
            "SELECT id FROM races WHERE season = %s AND round = %s",
            (season, round_num),
        )
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"No race in DB for {season} R{round_num}. Run ingest_fastf1 first.")
    return row[0]


def get_race_circuit(race_id: int) -> str:
    with cursor() as cur:
        cur.execute("SELECT circuit FROM races WHERE id = %s", (race_id,))
        return cur.fetchone()[0]


def load_race_history() -> pd.DataFrame:
    with cursor() as cur:
        cur.execute("""
            SELECT r.season, r.round, r.circuit,
                   rr.abbreviation, rr.position, rr.grid_position
            FROM race_results rr
            JOIN races r ON rr.race_id = r.id
            WHERE rr.position IS NOT NULL
        """)
        rows = cur.fetchall()
    return pd.DataFrame(
        rows,
        columns=["season", "round", "circuit", "abbreviation", "position", "grid_position"],
    )


def load_qualifying_for_race(race_id: int) -> pd.DataFrame:
    with cursor() as cur:
        cur.execute(
            "SELECT abbreviation, position FROM qualifying_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["abbreviation", "position"])


def get_markets_for_race(race_id: int, market_type: str) -> dict:
    """Returns {driver_abbreviation_or_name: (market_id, kalshi_mid)} using driver_name."""
    with cursor() as cur:
        cur.execute("""
            SELECT id, driver_name
            FROM markets
            WHERE race_id = %s AND market_type = %s AND status = 'open'
        """, (race_id, market_type))
        rows = cur.fetchall()
    return {row[1]: row[0] for row in rows}  # driver_name → market_id


def get_current_bankroll() -> float:
    with cursor() as cur:
        cur.execute("""
            SELECT bankroll_after FROM portfolio_snapshots
            ORDER BY snapshot_at DESC LIMIT 1
        """)
        row = cur.fetchone()
    return float(row[0]) if row else STARTING_BANKROLL


def save_predictions_and_get_ids(
    market_name_map: dict,
    predictions: list[dict],
    kalshi_mid_map: dict,
    abbrev_to_name: dict,
) -> dict:
    """
    Saves predictions to DB and returns {market_id: prediction_id}.
    market_name_map: {driver_name: market_id}
    abbrev_to_name: {abbreviation: driver_name}
    """
    pred_id_map = {}
    with cursor() as cur:
        for pred in predictions:
            abbrev = pred["abbreviation"]
            driver_name = abbrev_to_name.get(abbrev)
            if driver_name is None:
                continue
            market_id = market_name_map.get(driver_name)
            if market_id is None:
                continue
            kalshi_mid = kalshi_mid_map.get(market_id, 0.0)
            edge = round(pred["probability"] - kalshi_mid, 6)
            cur.execute("""
                INSERT INTO predictions
                    (market_id, oracle_probability, kalshi_mid_price, edge, model_version)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (market_id, pred["probability"], kalshi_mid, edge, MODEL_VERSION))
            pred_id = cur.fetchone()[0]
            pred_id_map[market_id] = pred_id
    return pred_id_map


def get_kalshi_mids(race_id: int, market_type: str) -> dict:
    """Returns {market_id: kalshi_mid_price} from most recent orderbook snapshots."""
    with cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (m.id) m.id, s.best_yes_ask, s.best_no_ask
            FROM markets m
            JOIN orderbook_snapshots s ON s.market_id = m.id
            WHERE m.race_id = %s AND m.market_type = %s
            ORDER BY m.id, s.snapshot_at DESC
        """, (race_id, market_type))
        rows = cur.fetchall()

    mids = {}
    for market_id, yes_ask, no_ask in rows:
        if yes_ask is not None and no_ask is not None:
            yes_bid = 1.0 - float(no_ask)
            mids[market_id] = (yes_bid + float(yes_ask)) / 2
        elif yes_ask is not None:
            mids[market_id] = float(yes_ask)
    return mids


def load_abbrev_to_name(race_id: int) -> dict:
    """Build {abbreviation: driver_name} from race_results for this race."""
    with cursor() as cur:
        cur.execute(
            "SELECT abbreviation, driver_name FROM race_results WHERE race_id = %s",
            (race_id,),
        )
        rows = cur.fetchall()
    if not rows:
        cur2_result = None
        with cursor() as cur:
            cur.execute(
                "SELECT abbreviation, driver_name FROM qualifying_results WHERE race_id = %s",
                (race_id,),
            )
            rows = cur.fetchall()
    return {r[0]: r[1] for r in rows}


def run_race(season: int, round_num: int, market_types: list[str]):
    race_id = get_race_id(season, round_num)
    circuit = get_race_circuit(race_id)
    console.print(f"Race: {season} R{round_num} — {circuit} (id={race_id})")

    history = load_race_history()
    if history.empty:
        raise RuntimeError("No historical race data in DB. Run ingest_historical.py first.")

    prior = history[
        (history["season"] < season)
        | ((history["season"] == season) & (history["round"] < round_num))
    ]
    console.print(f"Prior history: {len(prior)} driver-race rows")

    quali = load_qualifying_for_race(race_id)
    if quali.empty:
        console.print("[yellow]No qualifying data for this race — using race grid_position fallback[/]")
        with cursor() as cur:
            cur.execute(
                "SELECT abbreviation, grid_position FROM race_results WHERE race_id = %s AND grid_position IS NOT NULL",
                (race_id,),
            )
            rows = cur.fetchall()
        quali = pd.DataFrame(rows, columns=["abbreviation", "position"])

    if quali.empty:
        raise RuntimeError("No qualifying or grid position data. Ingest qualifying first.")

    features = build_race_features(
        results_history=prior,
        qualifying_df=quali,
        circuit=circuit,
        current_round=round_num,
        current_season=season,
        is_wet=False,
    )
    console.print(f"Built features for {len(features)} drivers")

    abbrev_to_name = load_abbrev_to_name(race_id)
    bankroll = get_current_bankroll()
    console.print(f"Current bankroll: ${bankroll:.2f}")

    for market_type in market_types:
        console.print(f"\n[bold]→ {market_type}[/]")
        try:
            model = load_model(market_type)
        except FileNotFoundError:
            console.print(f"[red]Model not found for {market_type}. Run build_training_data.py first.[/]")
            continue

        preds = predict_race(features, model)

        market_name_map = get_markets_for_race(race_id, market_type)
        if not market_name_map:
            console.print(f"[yellow]No open markets in DB for {market_type}. Run save_markets first.[/]")
            continue

        kalshi_mid_map = get_kalshi_mids(race_id, market_type)

        pred_id_map = save_predictions_and_get_ids(
            market_name_map, preds, kalshi_mid_map, abbrev_to_name
        )
        console.print(f"Saved {len(pred_id_map)} predictions")

        bet_inputs = [
            {
                "abbreviation": p["abbreviation"],
                "market_id": market_name_map.get(abbrev_to_name.get(p["abbreviation"], ""), 0),
                "oracle_probability": p["probability"],
                "kalshi_mid": kalshi_mid_map.get(
                    market_name_map.get(abbrev_to_name.get(p["abbreviation"], ""), 0), 0.0
                ),
            }
            for p in preds
            if abbrev_to_name.get(p["abbreviation"]) in market_name_map
        ]
        bets = compute_bets(bet_inputs, bankroll)
        n_bets = sum(1 for b in bets if b["bet_size"] > 0)
        save_bets(bets, pred_id_map)
        console.print(f"[green]Placed {n_bets} bets (edge ≥ {MIN_EDGE*100:.0f}%)[/]")

        for p in preds[:5]:
            abbrev = p["abbreviation"]
            name = abbrev_to_name.get(abbrev, abbrev)
            market_id = market_name_map.get(name, 0)
            mid = kalshi_mid_map.get(market_id, 0.0)
            edge = p["probability"] - mid
            console.print(
                f"  {abbrev:4s}  oracle={p['probability']*100:.1f}%  "
                f"kalshi={mid*100:.1f}%  edge={edge*100:+.1f}%"
            )


def main():
    parser = argparse.ArgumentParser(description="Run Oracle model for a race weekend")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True, dest="round_num")
    parser.add_argument(
        "--market-type",
        choices=MARKET_TYPES,
        default=None,
        help="Run only this market type (default: all)",
    )
    args = parser.parse_args()
    targets = [args.market_type] if args.market_type else MARKET_TYPES
    run_race(args.season, args.round_num, targets)


if __name__ == "__main__":
    main()
