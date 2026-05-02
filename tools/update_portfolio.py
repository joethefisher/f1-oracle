"""
Compute and save portfolio snapshot after a race is settled.

Usage:
    python tools/update_portfolio.py --race-id 1
"""
import argparse
from rich.console import Console

console = Console()

STARTING_BANKROLL = 1000.0


def apply_settled_bets(bankroll: float, bets: list[dict]) -> float:
    """
    Apply a list of settled bets to the bankroll.
    Each bet: {"bet_size": float, "kalshi_mid": float, "won": bool}
    """
    for bet in bets:
        size = bet["bet_size"]
        if size <= 0:
            continue
        if bet["won"]:
            bankroll += size * (1.0 / bet["kalshi_mid"] - 1.0)
        else:
            bankroll -= size
    return round(bankroll, 2)


def compute_return_pct(starting: float, current: float) -> float:
    return round((current - starting) / starting * 100.0, 4)


def compute_kalshi_baseline(
    markets: list[dict],
    bankroll: float,
    oracle_total_bet: float,
) -> list[dict]:
    """
    Spread oracle_total_bet proportionally across all markets by their Kalshi mid-price.
    Returns list of {"kalshi_mid": float, "bet_size": float} records.
    """
    total_price = sum(m["kalshi_mid"] for m in markets)
    if total_price == 0:
        return [{"kalshi_mid": m["kalshi_mid"], "bet_size": 0.0} for m in markets]
    return [
        {
            "kalshi_mid": m["kalshi_mid"],
            "bet_size": round(m["kalshi_mid"] / total_price * oracle_total_bet, 2),
        }
        for m in markets
    ]


def save_snapshot(race_id: int, bankroll: float, return_pct: float, kalshi_baseline: float):
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("""
            INSERT INTO portfolio_snapshots
                (race_id, bankroll_after, return_pct, kalshi_baseline_value, snapshot_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (race_id) DO UPDATE
                SET bankroll_after = EXCLUDED.bankroll_after,
                    return_pct = EXCLUDED.return_pct,
                    kalshi_baseline_value = EXCLUDED.kalshi_baseline_value,
                    snapshot_at = NOW()
        """, (race_id, bankroll, return_pct, kalshi_baseline))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-id", type=int, required=True)
    args = parser.parse_args()
    console.print(f"[yellow]update_portfolio requires settled outcomes in DB for race {args.race_id}[/]")


if __name__ == "__main__":
    main()
