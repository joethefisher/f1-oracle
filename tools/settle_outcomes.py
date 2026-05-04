"""
Settle virtual bets after a race by matching results to predictions.

Usage:
    python -m tools.settle_outcomes --season 2025 --round 6
    python -m tools.settle_outcomes --race-id 42
"""
import argparse
from rich.console import Console

from tools.train_model import MODEL_VERSION

console = Console()

_PODIUM_POSITIONS = {1, 2, 3}


def determine_winner(
    market_type: str,
    driver_abbreviation: str,
    race_results: dict,
    quali_results: dict | None = None,
) -> bool:
    """
    Determine if a YES bet resolves True.
    race_results: {abbreviation: finishing_position}
    quali_results: {abbreviation: qualifying_position}  (used for pole market)
    """
    if market_type == "pole":
        results = quali_results or race_results
    else:
        results = race_results

    position = results.get(driver_abbreviation)
    if position is None:
        return False
    if market_type == "race_winner":
        return position == 1
    if market_type == "podium":
        return position in _PODIUM_POSITIONS
    if market_type == "pole":
        return position == 1
    if market_type == "sprint":
        return position == 1
    return False


def compute_pnl(bet_size: float, kalshi_mid: float, won: bool) -> float:
    if bet_size <= 0:
        return 0.0
    if won:
        return bet_size * (1.0 / kalshi_mid - 1.0)
    return -bet_size


def settle_race(race_id: int):
    """Query DB, match results to virtual bets, write outcomes."""
    from tools.db import cursor

    with cursor() as cur:
        cur.execute("""
            SELECT m.id, m.market_type, m.driver_abbreviation,
                   p.id AS pred_id, p.kalshi_mid_price,
                   vb.id AS bet_id, vb.bet_size_dollars
            FROM markets m
            JOIN predictions p ON p.market_id = m.id AND p.model_version = %s
            JOIN virtual_bets vb ON vb.prediction_id = p.id
            WHERE m.race_id = %s
        """, (MODEL_VERSION, race_id,))
        bets = cur.fetchall()

        cur.execute(
            "SELECT abbreviation, position FROM race_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        race_results = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute(
            "SELECT abbreviation, position FROM qualifying_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        quali_results = {r[0]: r[1] for r in cur.fetchall()}

    settled = 0
    with cursor() as cur:
        for row in bets:
            market_id, market_type, abbrev, pred_id, kalshi_mid, bet_id, bet_size = row

            won = determine_winner(
                market_type,
                abbrev or "",
                race_results,
                quali_results if quali_results else None,
            )

            cur.execute("""
                INSERT INTO outcomes (market_id, winning_side, settled_at, source)
                VALUES (%s, %s, NOW(), 'fastf1')
                ON CONFLICT (market_id) DO UPDATE SET winning_side = EXCLUDED.winning_side
            """, (market_id, "yes" if won else "no"))
            settled += 1

    console.print(f"[green]Settled {settled} outcomes for race {race_id}[/]")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--race-id", type=int)
    group.add_argument("--season", type=int)
    parser.add_argument("--round", type=int, dest="round_num")
    args = parser.parse_args()

    if args.race_id:
        race_id = args.race_id
    else:
        if not args.round_num:
            parser.error("--round is required when using --season")
        from tools.db import cursor
        with cursor() as cur:
            cur.execute(
                "SELECT id FROM races WHERE season = %s AND round = %s",
                (args.season, args.round_num),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"No race found for {args.season} R{args.round_num}")
        race_id = row[0]

    settle_race(race_id)


if __name__ == "__main__":
    main()
