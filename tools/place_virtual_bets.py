"""
Compute and log half-Kelly virtual bets for a set of predictions.

Usage:
    python tools/place_virtual_bets.py --race-id 1
"""
import argparse
from rich.console import Console

from tools.portfolio import half_kelly_bet_size, MIN_EDGE

console = Console()


def compute_bets(predictions: list[dict], bankroll: float) -> list[dict]:
    """
    Given predictions (each with oracle_probability and kalshi_mid),
    return bet records with bet_size, kelly_fraction, bankroll_at_time.
    """
    bets = []
    for pred in predictions:
        oracle_prob = pred["oracle_probability"]
        kalshi_mid = pred["kalshi_mid"]
        edge = oracle_prob - kalshi_mid
        bet_size = half_kelly_bet_size(oracle_prob, kalshi_mid, bankroll)
        denominator = 1.0 - kalshi_mid
        kelly_fraction = (edge / denominator) if (edge >= MIN_EDGE and denominator > 0) else 0.0
        bets.append({
            "abbreviation": pred["abbreviation"],
            "market_id": pred["market_id"],
            "oracle_probability": oracle_prob,
            "kalshi_mid": kalshi_mid,
            "edge": round(edge, 6),
            "kelly_fraction": round(kelly_fraction, 6),
            "bet_size": bet_size,
            "bankroll_at_time": bankroll,
        })
    return bets


def save_bets(bets: list[dict], prediction_id_map: dict):
    """Write bet records to virtual_bets table. prediction_id_map: {market_id: prediction_id}.

    Snapshots the Kalshi mid and oracle prob into the bet row so P&L and
    post-mortems don't depend on predictions.kalshi_mid_price (which run_model
    overwrites on every run, including post-race when the book has resolved).
    """
    from tools.db import cursor
    with cursor() as cur:
        for bet in bets:
            if bet["bet_size"] <= 0:
                continue
            pred_id = prediction_id_map.get(bet["market_id"])
            if pred_id is None:
                continue
            kalshi_mid = bet.get("kalshi_mid")
            oracle_prob = bet.get("oracle_probability")
            cur.execute("""
                INSERT INTO virtual_bets
                    (prediction_id, bet_size_dollars, kelly_fraction, bankroll_at_time,
                     kalshi_mid_at_bet, oracle_prob_at_bet)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (prediction_id) DO UPDATE
                    SET bet_size_dollars   = EXCLUDED.bet_size_dollars,
                        kelly_fraction     = EXCLUDED.kelly_fraction,
                        bankroll_at_time   = EXCLUDED.bankroll_at_time,
                        kalshi_mid_at_bet  = EXCLUDED.kalshi_mid_at_bet,
                        oracle_prob_at_bet = EXCLUDED.oracle_prob_at_bet
            """, (pred_id, bet["bet_size"], bet["kelly_fraction"], bet["bankroll_at_time"],
                  kalshi_mid, oracle_prob))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-id", type=int, required=True)
    args = parser.parse_args()
    console.print(f"[yellow]place_virtual_bets requires predictions in DB for race {args.race_id}[/]")


if __name__ == "__main__":
    main()
