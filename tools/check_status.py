"""
Print system status: DB data counts, trained models, upcoming races.

Usage:
    python -m tools.check_status
"""
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

MODEL_DIR = Path(__file__).parent.parent / ".tmp" / "models"


def check_db():
    from tools.db import cursor
    console.rule("[bold]Database")

    with cursor() as cur:
        cur.execute("SELECT season, COUNT(DISTINCT rr.race_id), COUNT(*), SUM(CASE WHEN rr.position IS NOT NULL THEN 1 ELSE 0 END) FROM race_results rr JOIN races r ON rr.race_id=r.id GROUP BY season ORDER BY season")
        race_rows = cur.fetchall()

        cur.execute("SELECT season, COUNT(DISTINCT qr.race_id), COUNT(*), SUM(CASE WHEN qr.position IS NOT NULL THEN 1 ELSE 0 END) FROM qualifying_results qr JOIN races r ON qr.race_id=r.id GROUP BY season ORDER BY season")
        quali_rows = cur.fetchall()

        cur.execute("SELECT status, COUNT(*) FROM races GROUP BY status ORDER BY status")
        race_status = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM predictions")
        n_preds = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM virtual_bets")
        n_bets = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM outcomes")
        n_outcomes = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        n_snaps = cur.fetchone()[0]

    t = Table(title="Race Results by Season")
    t.add_column("Season")
    t.add_column("Races", justify="right")
    t.add_column("Rows", justify="right")
    t.add_column("With Position", justify="right")
    for row in race_rows:
        t.add_row(str(row[0]), str(row[1]), str(row[2]), str(row[3]))
    console.print(t)

    t2 = Table(title="Qualifying Results by Season")
    t2.add_column("Season")
    t2.add_column("Races", justify="right")
    t2.add_column("Rows", justify="right")
    t2.add_column("With Position", justify="right")
    for row in quali_rows:
        t2.add_row(str(row[0]), str(row[1]), str(row[2]), str(row[3]))
    console.print(t2)

    console.print(f"Race statuses: {dict(race_status)}")
    console.print(f"Predictions: {n_preds} | Virtual bets: {n_bets} | Outcomes: {n_outcomes} | Portfolio snaps: {n_snaps}")


def check_models():
    console.rule("[bold]Trained Models")
    if not MODEL_DIR.exists():
        console.print("[yellow]No models directory (.tmp/models/)[/]")
        return
    models = list(MODEL_DIR.glob("*.joblib"))
    if not models:
        console.print("[yellow]No trained models found[/]")
    for m in models:
        size = m.stat().st_size
        console.print(f"  [green]✓[/] {m.stem} ({size:,} bytes)")


def check_upcoming():
    console.rule("[bold]Upcoming Races")
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("""
            SELECT season, round, name, circuit, race_date_utc, status
            FROM races
            WHERE status IN ('upcoming', 'active')
            ORDER BY race_date_utc NULLS LAST
            LIMIT 5
        """)
        rows = cur.fetchall()

    if not rows:
        console.print("[yellow]No upcoming/active races in DB[/]")
        console.print("  Run: python -m tools.setup_race --season 2025 --round <N>")
    else:
        t = Table(title="Upcoming")
        t.add_column("Season/Round")
        t.add_column("Name")
        t.add_column("Circuit")
        t.add_column("Date")
        t.add_column("Status")
        for r in rows:
            t.add_row(f"{r[0]} R{r[1]}", r[2], r[3], str(r[4])[:10] if r[4] else "—", r[5])
        console.print(t)


def main():
    try:
        check_db()
    except Exception as e:
        console.print(f"[red]DB check failed: {e}[/]")
    check_models()
    try:
        check_upcoming()
    except Exception as e:
        console.print(f"[red]Upcoming check failed: {e}[/]")


if __name__ == "__main__":
    main()
