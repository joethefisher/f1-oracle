"""
Evaluate Oracle prediction accuracy and virtual P&L on historical data.

Usage:
    python tools/backtest.py --market-type race_winner
"""
import argparse
from dataclasses import dataclass
import pandas as pd
from rich.console import Console

console = Console()


@dataclass
class BacktestResult:
    hit_rate: float
    total_pnl: float
    n_bets: int
    n_wins: int


def compute_hit_rate(df: pd.DataFrame) -> float:
    bets = df[df["bet_size"] > 0]
    if len(bets) == 0:
        return 0.0
    return float(bets["won"].sum() / len(bets))


def compute_virtual_pnl(df: pd.DataFrame) -> float:
    total = 0.0
    for _, row in df.iterrows():
        if row["bet_size"] <= 0:
            continue
        if row["won"]:
            total += row["bet_size"] * (1.0 / row["kalshi_mid"] - 1.0)
        else:
            total -= row["bet_size"]
    return total


def run_backtest(df: pd.DataFrame) -> BacktestResult:
    bets = df[df["bet_size"] > 0]
    return BacktestResult(
        hit_rate=compute_hit_rate(df),
        total_pnl=round(compute_virtual_pnl(df), 2),
        n_bets=len(bets),
        n_wins=int(bets["won"].sum()),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-type", default="race_winner",
                        choices=["race_winner", "podium", "pole", "sprint"])
    args = parser.parse_args()
    console.print("[yellow]Backtest requires DATABASE_URL and historical data. Run ingest_historical.py first.[/]")


if __name__ == "__main__":
    main()
