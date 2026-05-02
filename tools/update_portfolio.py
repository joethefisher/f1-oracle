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


def compute_kalshi_baseline_pnl(
    bets: list[dict],
    oracle_total_bet: float,
) -> float:
    """
    Compute P&L for a bettor who spreads oracle_total_bet proportionally
    by Kalshi mid-price and resolves at actual outcomes.
    bets: [{"kalshi_mid": float, "won": bool}]
    """
    total_price = sum(b["kalshi_mid"] for b in bets if b["kalshi_mid"] > 0)
    if total_price == 0 or oracle_total_bet == 0:
        return 0.0
    pnl = 0.0
    for bet in bets:
        mid = bet["kalshi_mid"]
        if mid <= 0:
            continue
        size = round(mid / total_price * oracle_total_bet, 2)
        if bet["won"]:
            pnl += size * (1.0 / mid - 1.0)
        else:
            pnl -= size
    return round(pnl, 2)


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


def compute_and_save(race_id: int):
    from tools.db import cursor

    with cursor() as cur:
        cur.execute("""
            SELECT vb.bet_size_dollars, p.kalshi_mid_price, o.winning_side
            FROM virtual_bets vb
            JOIN predictions p ON vb.prediction_id = p.id
            JOIN markets m ON p.market_id = m.id
            LEFT JOIN outcomes o ON o.market_id = m.id
            WHERE m.race_id = %s
        """, (race_id,))
        rows = cur.fetchall()

    if not rows:
        console.print(f"[yellow]No settled bets found for race {race_id}[/]")
        return

    # Get previous bankroll
    from tools.db import cursor as cur_ctx
    with cur_ctx() as cur:
        cur.execute("""
            SELECT bankroll_after FROM portfolio_snapshots
            ORDER BY snapshot_at DESC LIMIT 1
        """)
        prev = cur.fetchone()
    bankroll = float(prev[0]) if prev else STARTING_BANKROLL

    bets = [
        {
            "bet_size": float(r[0]) if r[0] else 0.0,
            "kalshi_mid": float(r[1]) if r[1] else 0.5,
            "won": r[2] == "yes",
        }
        for r in rows
    ]

    oracle_total_bet = sum(b["bet_size"] for b in bets)
    new_bankroll = apply_settled_bets(bankroll, bets)
    return_pct = compute_return_pct(STARTING_BANKROLL, new_bankroll)

    # Kalshi baseline: spread oracle_total_bet proportionally by kalshi_mid, use actual outcomes
    baseline_pnl = compute_kalshi_baseline_pnl(bets, oracle_total_bet)
    baseline_value = bankroll + baseline_pnl

    save_snapshot(race_id, new_bankroll, return_pct, round(baseline_value, 2))
    console.print(f"[green]Portfolio updated: ${bankroll:.2f} → ${new_bankroll:.2f} ({return_pct:+.2f}%)[/]")


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

    compute_and_save(race_id)


if __name__ == "__main__":
    main()
