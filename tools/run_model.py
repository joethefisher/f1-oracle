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
from tools.train_model import FEATURE_COLS, MODEL_VERSION, load_model
from tools.elo import get_driver_elo_snapshot, get_constructor_elo_snapshot
from tools.team_rosters import TEAM_ROSTERS
from tools.place_virtual_bets import compute_bets, save_bets
from tools.portfolio import MIN_EDGE

console = Console()

STARTING_BANKROLL = 1000.0
MARKET_TYPES = ["race_winner", "podium", "pole"]


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


def load_qualifying_history() -> pd.DataFrame:
    """Load all qualifying results for Elo computation."""
    with cursor() as cur:
        cur.execute("""
            SELECT r.season, r.round, qr.abbreviation, qr.position
            FROM qualifying_results qr
            JOIN races r ON qr.race_id = r.id
            WHERE qr.position IS NOT NULL
        """)
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["season", "round", "abbreviation", "position"])


def load_qualifying_for_race(race_id: int) -> pd.DataFrame:
    with cursor() as cur:
        cur.execute(
            "SELECT abbreviation, position FROM qualifying_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["abbreviation", "position"])


def get_markets_for_race(race_id: int, market_type: str) -> dict:
    """Returns {abbreviation: market_id} using driver_abbreviation from ticker."""
    with cursor() as cur:
        cur.execute("""
            SELECT id, driver_abbreviation
            FROM markets
            WHERE race_id = %s AND market_type = %s AND status IN ('open', 'active')
              AND driver_abbreviation IS NOT NULL
        """, (race_id, market_type))
        rows = cur.fetchall()
    return {row[1]: row[0] for row in rows}


def get_current_bankroll() -> float:
    with cursor() as cur:
        cur.execute("""
            SELECT bankroll_after FROM portfolio_snapshots
            ORDER BY snapshot_at DESC LIMIT 1
        """)
        row = cur.fetchone()
    return float(row[0]) if row else STARTING_BANKROLL


def purge_stale_bets(race_id: int) -> int:
    """Delete virtual_bets for this race that belong to a different model version.

    Called before placing new bets so only one model version's bets exist per race.
    Returns the number of bets deleted.
    """
    with cursor() as cur:
        cur.execute("""
            DELETE FROM virtual_bets
            WHERE prediction_id IN (
                SELECT p.id FROM predictions p
                JOIN markets m ON p.market_id = m.id
                WHERE m.race_id = %s AND p.model_version != %s
            )
        """, (race_id, MODEL_VERSION))
        return cur.rowcount


def save_predictions_and_get_ids(
    market_abbrev_map: dict,
    predictions: list[dict],
    kalshi_mid_map: dict,
) -> dict:
    """
    Saves predictions to DB and returns {market_id: prediction_id}.
    market_abbrev_map: {abbreviation: market_id}
    """
    pred_id_map = {}
    with cursor() as cur:
        for pred in predictions:
            abbrev = pred["abbreviation"]
            market_id = market_abbrev_map.get(abbrev)
            if market_id is None:
                continue
            kalshi_mid = kalshi_mid_map.get(market_id, 0.0)
            edge = round(pred["probability"] - kalshi_mid, 6)
            cur.execute("""
                INSERT INTO predictions
                    (market_id, oracle_probability, kalshi_mid_price, edge, model_version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (market_id, model_version) DO UPDATE
                    SET oracle_probability = EXCLUDED.oracle_probability,
                        kalshi_mid_price   = EXCLUDED.kalshi_mid_price,
                        edge               = EXCLUDED.edge,
                        predicted_at       = NOW()
                RETURNING id
            """, (market_id, pred["probability"], kalshi_mid, edge, MODEL_VERSION))
            pred_id = cur.fetchone()[0]
            pred_id_map[market_id] = pred_id
    return pred_id_map


def get_kalshi_mids(race_id: int, market_type: str) -> dict:
    """Returns {market_id: kalshi_mid_price} from most recent orderbook snapshots."""
    with cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (m.id) m.id, s.best_yes_bid, s.best_yes_ask
            FROM markets m
            JOIN orderbook_snapshots s ON s.market_id = m.id
            WHERE m.race_id = %s AND m.market_type = %s
            ORDER BY m.id, s.snapshot_at DESC
        """, (race_id, market_type))
        rows = cur.fetchall()

    mids = {}
    for market_id, yes_bid, yes_ask in rows:
        if yes_bid is not None and yes_ask is not None:
            mids[market_id] = (float(yes_bid) + float(yes_ask)) / 2
        elif yes_ask is not None:
            mids[market_id] = float(yes_ask)
        elif yes_bid is not None:
            mids[market_id] = float(yes_bid)
    return mids


def run_race(season: int, round_num: int, market_types: list[str], is_wet: bool = False):
    race_id = get_race_id(season, round_num)
    circuit = get_race_circuit(race_id)
    console.print(f"Race: {season} R{round_num} — {circuit} (id={race_id})")

    history = load_race_history()
    if history.empty:
        raise RuntimeError("No historical race data in DB. Run ingest_historical.py first.")

    quali_history = load_qualifying_history()

    prior = history[
        (history["season"] < season)
        | ((history["season"] == season) & (history["round"] < round_num))
    ]
    console.print(f"Prior history: {len(prior)} driver-race rows")

    # Elo ratings going into this race
    driver_elo = get_driver_elo_snapshot(history, season, round_num)
    constructor_elo = get_constructor_elo_snapshot(quali_history, season, round_num, TEAM_ROSTERS)
    console.print(f"Elo computed: {len(driver_elo)} drivers, {len(constructor_elo)} constructors")

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
        is_wet=is_wet,
        driver_elo_snapshot=driver_elo,
        constructor_elo_snapshot=constructor_elo,
        team_rosters=TEAM_ROSTERS,
    )
    console.print(f"Built features for {len(features)} drivers")

    bankroll = get_current_bankroll()
    console.print(f"Current bankroll: ${bankroll:.2f}")

    for market_type in market_types:
        console.print(f"\n[bold]→ {market_type}[/]")
        try:
            model = load_model(market_type)
        except FileNotFoundError:
            console.print(f"[red]Model not found for {market_type}. Run build_training_data first.[/]")
            continue

        preds = predict_race(features, model)

        market_abbrev_map = get_markets_for_race(race_id, market_type)
        if not market_abbrev_map:
            console.print(f"[yellow]No open markets in DB for {market_type}. Run save_markets first.[/]")
            continue

        kalshi_mid_map = get_kalshi_mids(race_id, market_type)

        pred_id_map = save_predictions_and_get_ids(
            market_abbrev_map, preds, kalshi_mid_map
        )
        console.print(f"Saved {len(pred_id_map)} predictions (model_version={MODEL_VERSION})")

        bet_inputs = [
            {
                "abbreviation": p["abbreviation"],
                "market_id": market_abbrev_map.get(p["abbreviation"], 0),
                "oracle_probability": p["probability"],
                "kalshi_mid": kalshi_mid_map.get(market_abbrev_map.get(p["abbreviation"], 0), 0.0),
            }
            for p in preds
            if p["abbreviation"] in market_abbrev_map
        ]
        bets = compute_bets(bet_inputs, bankroll)
        n_bets = sum(1 for b in bets if b["bet_size"] > 0)
        purged = purge_stale_bets(race_id)
        if purged:
            console.print(f"[yellow]Purged {purged} stale bets from other model versions[/]")
        save_bets(bets, pred_id_map)
        console.print(f"[green]Placed {n_bets} bets (edge ≥ {MIN_EDGE*100:.0f}%)[/]")

        for p in preds[:5]:
            abbrev = p["abbreviation"]
            market_id = market_abbrev_map.get(abbrev, 0)
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
    parser.add_argument("--wet", action="store_true", help="Flag race conditions as wet")
    args = parser.parse_args()
    targets = [args.market_type] if args.market_type else MARKET_TYPES
    run_race(args.season, args.round_num, targets, is_wet=args.wet)


if __name__ == "__main__":
    main()
