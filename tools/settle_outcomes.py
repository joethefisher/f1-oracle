"""
Settle virtual bets after a race by matching results to predictions.

Usage:
    python tools/settle_outcomes.py --race-id 1
"""
import argparse
from rich.console import Console

console = Console()

_PODIUM_POSITIONS = {1, 2, 3}


def determine_winner(
    market_type: str,
    driver_abbreviation: str,
    race_results: dict,
) -> bool:
    """
    Determine if a YES bet on driver_abbreviation resolves True.
    race_results: {abbreviation: finishing_position}
    """
    position = race_results.get(driver_abbreviation)
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
    """Query DB, match results to virtual bets, write outcomes and P&L."""
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("""
            SELECT m.id, m.market_type, m.driver_name,
                   p.id as pred_id, p.kalshi_mid_price,
                   vb.id as bet_id, vb.bet_size_dollars
            FROM markets m
            JOIN predictions p ON p.market_id = m.id
            JOIN virtual_bets vb ON vb.prediction_id = p.id
            WHERE m.race_id = %s
        """, (race_id,))
        rows = cur.fetchall()

        cur.execute("""
            SELECT abbreviation, position FROM race_results
            WHERE race_id = %s
        """, (race_id,))
        results_rows = cur.fetchall()

    race_results = {r[0]: r[1] for r in results_rows}

    with cursor() as cur:
        for row in rows:
            market_id, market_type, driver_name, pred_id, kalshi_mid, bet_id, bet_size = row
            abbrev = driver_name.split()[-1].upper() if driver_name else ""
            won = determine_winner(market_type, abbrev, race_results)
            pnl = compute_pnl(bet_size or 0.0, kalshi_mid or 0.5, won)
            cur.execute("""
                INSERT INTO outcomes (market_id, winning_side, settled_at, source)
                VALUES (%s, %s, NOW(), 'fastf1')
                ON CONFLICT (market_id) DO UPDATE SET winning_side = EXCLUDED.winning_side
            """, (market_id, "yes" if won else "no"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-id", type=int, required=True)
    args = parser.parse_args()
    settle_race(args.race_id)
    console.print(f"[green]Settled race {args.race_id}[/]")


if __name__ == "__main__":
    main()
