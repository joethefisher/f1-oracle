"""
Verify database schema by printing table names and row counts.

Usage:
    python tools/db_verify.py
"""

from tools.db import cursor
from rich.console import Console
from rich.table import Table

TABLES = [
    "races", "markets", "predictions", "virtual_bets",
    "outcomes", "portfolio_snapshots", "race_results", "qualifying_results",
]
console = Console()


def verify_db():
    tbl = Table(title="Database Status")
    tbl.add_column("Table", style="cyan")
    tbl.add_column("Rows", justify="right")

    with cursor() as cur:
        for t in TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                tbl.add_row(t, str(count))
            except Exception as e:
                tbl.add_row(t, f"[red]ERROR: {e}[/]")

    console.print(tbl)


if __name__ == "__main__":
    verify_db()
