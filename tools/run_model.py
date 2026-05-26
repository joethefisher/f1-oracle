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
from tools.build_features import build_race_features, build_prequali_features
from tools.train_model import (
    FEATURE_COLS, FEATURE_COLS_POLE, MODEL_VERSION, load_model, feature_cols_for,
)
from tools.elo import get_driver_elo_snapshot, get_constructor_elo_snapshot
from tools.team_rosters import TEAM_ROSTERS
from tools.place_virtual_bets import compute_bets, save_bets
from tools.portfolio import MIN_EDGE
from tools.kelly_portfolio import size_portfolio
from tools.validate import validate_distribution, is_strict, ValidationError

console = Console()

STARTING_BANKROLL = 1000.0
MARKET_TYPES = ["race_winner", "podium", "pole"]

# How many drivers satisfy each market per race. Probabilities across all drivers
# for a market must sum to this: exactly one race winner / pole-sitter, but three
# drivers finish on the podium. Normalizing podium to 1 (instead of 3) understates
# every driver's podium probability ~3x and suppresses all podium edges.
MARKET_TARGET_SUM = {"race_winner": 1.0, "podium": 3.0, "pole": 1.0, "sprint": 1.0}


def normalize_probabilities(raw_probs: np.ndarray, target: float = 1.0) -> np.ndarray:
    total = raw_probs.sum()
    if total == 0:
        return np.full_like(raw_probs, target / len(raw_probs))
    return raw_probs / total * target


def predict_race(features_df: pd.DataFrame, model, target_sum: float = 1.0,
                 feature_cols: list[str] = FEATURE_COLS) -> list[dict]:
    X = features_df[feature_cols].values.astype(float)
    raw_probs = model.predict_proba(X)[:, 1]
    normalized = normalize_probabilities(raw_probs, target_sum)
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
            # Store the Oracle's probability always (the public site shows it), but
            # leave price/edge NULL when there's no live price — never invent a 0
            # mid, which would read as a full-probability edge and trigger a bet.
            mid = kalshi_mid_map.get(market_id)
            has_price = mid is not None and 0 < mid < 1
            kalshi_mid = mid if has_price else None
            edge = round(pred["probability"] - mid, 6) if has_price else None
            # Freeze the prediction row once the market has an outcome — a
            # post-race run_model otherwise overwrites kalshi_mid_price/edge with
            # the resolved 99c/1c values, destroying the bot's history. The
            # WHERE skips the UPDATE for settled markets; when that happens
            # RETURNING yields no row, so we look up the existing id explicitly.
            cur.execute("""
                INSERT INTO predictions
                    (market_id, oracle_probability, kalshi_mid_price, edge, model_version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (market_id, model_version) DO UPDATE
                    SET oracle_probability = EXCLUDED.oracle_probability,
                        kalshi_mid_price   = EXCLUDED.kalshi_mid_price,
                        edge               = EXCLUDED.edge,
                        predicted_at       = NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM outcomes o WHERE o.market_id = predictions.market_id
                    )
                RETURNING id
            """, (market_id, pred["probability"], kalshi_mid, edge, MODEL_VERSION))
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "SELECT id FROM predictions WHERE market_id = %s AND model_version = %s",
                    (market_id, MODEL_VERSION),
                )
                row = cur.fetchone()
            pred_id = row[0]
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

    market_preds: dict[str, list[dict]] = {}
    contexts = []
    for market_type in market_types:
        console.print(f"\n[bold]→ {market_type}[/]")
        try:
            model = load_model(market_type)
        except FileNotFoundError:
            console.print(f"[red]Model not found for {market_type}. Run build_training_data first.[/]")
            continue

        preds = predict_race(
            features, model, MARKET_TARGET_SUM.get(market_type, 1.0),
            feature_cols=feature_cols_for(market_type),
        )
        market_preds[market_type] = preds
        ctx = _save_and_validate_market(race_id, market_type, preds)
        if ctx:
            contexts.append(ctx)

    # Race ordering is driven by win probabilities; race_winner + podium are sized
    # jointly off that shared ordering. Fall back to the first available market.
    strengths = _strengths_from(market_preds.get("race_winner") or next(iter(market_preds.values()), []))
    _place_batch_bets(race_id, contexts, strengths, bankroll)


def _strengths_from(preds: list[dict]) -> dict[str, float]:
    return {p["abbreviation"]: p["probability"] for p in preds}


def _clear_bets_for_markets(race_id: int, market_types: list[str]) -> int:
    """Delete current-version bets for a race within the given market types.

    Lets bet placement be fully idempotent: re-running replaces the batch instead
    of leaving behind bets the optimizer no longer selects.
    """
    if not market_types:
        return 0
    with cursor() as cur:
        cur.execute("""
            DELETE FROM virtual_bets
            WHERE prediction_id IN (
                SELECT p.id FROM predictions p
                JOIN markets m ON p.market_id = m.id
                WHERE m.race_id = %s AND p.model_version = %s
                  AND m.market_type = ANY(%s)
            )
        """, (race_id, MODEL_VERSION, market_types))
        return cur.rowcount


def _save_and_validate_market(race_id: int, market_type: str, preds: list[dict]) -> dict | None:
    """Persist a market's predictions and validate them.

    Returns a betting context (markets/prices/prediction ids) when the market is
    safe to bet, or None when there are no markets or validation failed. Predictions
    are always stored (the public site shows them) regardless of the return value.
    """
    market_abbrev_map = get_markets_for_race(race_id, market_type)
    if not market_abbrev_map:
        console.print(f"[yellow]No open markets in DB for {market_type}. Run save_markets first.[/]")
        return None

    kalshi_mid_map = get_kalshi_mids(race_id, market_type)
    pred_id_map = save_predictions_and_get_ids(market_abbrev_map, preds, kalshi_mid_map)
    console.print(f"Saved {len(pred_id_map)} predictions (model_version={MODEL_VERSION})")

    # Validate the probability distribution before risking any bets. A failure
    # blocks only betting for this market — unless STRICT_VALIDATION is set.
    problems = validate_distribution(
        market_type, [p["probability"] for p in preds],
        MARKET_TARGET_SUM.get(market_type, 1.0),
    )
    if problems:
        for prob in problems:
            console.print(f"[red]VALIDATION FAIL: {prob}[/]")
        if is_strict():
            raise ValidationError("; ".join(problems))
        console.print(f"[yellow]Skipping bets for {market_type} (validation failed)[/]")
        return None

    return {
        "market_type": market_type,
        "preds": preds,
        "market_abbrev_map": market_abbrev_map,
        "kalshi_mid_map": kalshi_mid_map,
        "pred_id_map": pred_id_map,
    }


def _place_batch_bets(race_id: int, contexts: list[dict], strengths: dict[str, float],
                      bankroll: float):
    """Size and persist a correlated batch of bets with joint half-Kelly.

    Builds candidate bets across all validated markets, sizes them jointly off a
    simulated finishing order (so correlated podium/winner bets aren't over-staked),
    and writes the non-zero stakes. A missing/degenerate price is never a candidate.
    """
    candidates = []
    skipped_no_price = 0
    for ctx in contexts:
        for p in ctx["preds"]:
            market_id = ctx["market_abbrev_map"].get(p["abbreviation"])
            if market_id is None:
                continue
            mid = ctx["kalshi_mid_map"].get(market_id)
            if mid is None or not (0 < mid < 1):
                skipped_no_price += 1
                continue
            candidates.append({
                "market_type": ctx["market_type"],
                "driver": p["abbreviation"],
                "price": mid,
                "oracle_prob": p["probability"],
                "market_id": market_id,
                "prediction_id": ctx["pred_id_map"].get(market_id),
            })
    if skipped_no_price:
        console.print(f"[yellow]{skipped_no_price} market(s) had no live price — not betting them[/]")
    if not candidates:
        console.print("[yellow]No bettable candidates.[/]")
        return

    sized = size_portfolio(candidates, strengths, bankroll)

    bets, pred_id_map = [], {}
    for s in sized:
        if s["bet_size"] > 0 and s.get("prediction_id") is not None:
            bets.append({
                "market_id": s["market_id"],
                "bet_size": s["bet_size"],
                "kelly_fraction": s["fraction"],
                "bankroll_at_time": bankroll,
                # Snapshot the price paid and the model's view at bet time so
                # later re-runs (which overwrite predictions.kalshi_mid_price)
                # can't corrupt P&L or post-mortems.
                "kalshi_mid": s["price"],
                "oracle_probability": s["oracle_prob"],
            })
            pred_id_map[s["market_id"]] = s["prediction_id"]

    purged = purge_stale_bets(race_id)
    if purged:
        console.print(f"[yellow]Purged {purged} stale bets from other model versions[/]")
    # Clear this batch's existing bets so markets the optimizer no longer selects
    # (e.g. a bet whose edge has decayed) don't linger. Scoped to the batch's
    # market types, so pole bets placed in a separate pre-quali phase survive.
    batch_types = sorted({ctx["market_type"] for ctx in contexts})
    cleared = _clear_bets_for_markets(race_id, batch_types)
    if cleared:
        console.print(f"[yellow]Cleared {cleared} prior {batch_types} bets before re-sizing[/]")
    save_bets(bets, pred_id_map)
    total = sum(b["bet_size"] for b in bets)
    console.print(
        f"[green]Placed {len(bets)} joint half-Kelly bets — "
        f"${total:.2f} staked ({total / bankroll * 100:.1f}% of bankroll)[/]"
    )
    for s in sorted(sized, key=lambda x: x["bet_size"], reverse=True):
        if s["bet_size"] <= 0:
            continue
        edge = s["oracle_prob"] - s["price"]
        console.print(
            f"  {s['market_type']:11s} {s['driver']:4s}  oracle={s['oracle_prob']*100:.1f}%  "
            f"kalshi={s['price']*100:.1f}%  edge={edge*100:+.1f}%  bet=${s['bet_size']:.2f}"
        )


def run_pole_prequali(season: int, round_num: int, is_wet: bool = False):
    """Predict pole BEFORE qualifying, while the outcome is still uncertain.

    Uses the grid-free pole model (FEATURE_COLS_POLE) over the drivers that have
    open pole markets. Never run once qualifying is decided — that would be
    betting a known result.
    """
    race_id = get_race_id(season, round_num)
    circuit = get_race_circuit(race_id)
    console.print(f"Pole (pre-qualifying): {season} R{round_num} — {circuit} (id={race_id})")

    market_abbrev_map = get_markets_for_race(race_id, "pole")
    if not market_abbrev_map:
        console.print("[yellow]No open pole markets in DB. Run discovery first.[/]")
        return
    drivers = list(market_abbrev_map.keys())

    history = load_race_history()
    if history.empty:
        raise RuntimeError("No historical race data in DB.")
    quali_history = load_qualifying_history()
    prior = history[
        (history["season"] < season)
        | ((history["season"] == season) & (history["round"] < round_num))
    ]
    driver_elo = get_driver_elo_snapshot(history, season, round_num)
    constructor_elo = get_constructor_elo_snapshot(quali_history, season, round_num, TEAM_ROSTERS)

    features = build_prequali_features(
        results_history=prior,
        drivers=drivers,
        circuit=circuit,
        current_season=season,
        is_wet=is_wet,
        driver_elo_snapshot=driver_elo,
        constructor_elo_snapshot=constructor_elo,
        team_rosters=TEAM_ROSTERS,
    )
    console.print(f"Built pre-quali features for {len(features)} drivers")

    model = load_model("pole")
    preds = predict_race(features, model, MARKET_TARGET_SUM.get("pole", 1.0),
                         feature_cols=FEATURE_COLS_POLE)
    bankroll = get_current_bankroll()
    ctx = _save_and_validate_market(race_id, "pole", preds)
    if ctx:
        # Pole is its own correlated batch (one pole-sitter); strengths are the
        # pole probabilities themselves.
        _place_batch_bets(race_id, [ctx], _strengths_from(preds), bankroll)


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
