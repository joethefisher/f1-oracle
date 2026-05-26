"""
Post-weekend favorites-faded analysis.

Answers the question "why didn't the bot bet on the favorites?" by
reconstructing, for each market, the *real* Kalshi price at the moment the bot
placed its bets — read from `orderbook_snapshots` history, NOT from
`predictions.kalshi_mid_price`/`edge`, which `run_model` overwrites on every run
(including post-race re-runs, when the book has resolved to ~99c/1c). The
predictions columns are therefore useless for a post-mortem; the orderbook
history is the only faithful record of what the bot actually saw.

A "favorite" is a driver among the top-priced for its market. The bot only takes
positive-edge YES positions, so any favorite the model rates *below* the market
is structurally un-bettable — it gets faded. This tool surfaces those faded
favorites and flags the painful case: a heavy favorite the model faded that then
won.

Usage:
    python -m tools.review_weekend --race-id 260
    python -m tools.review_weekend --season 2026 --round 5
"""
import argparse

from rich.console import Console
from rich.table import Table

from tools.kalshi import compute_mid
from tools.portfolio import MIN_EDGE
from tools.settle_outcomes import compute_pnl, determine_winner
from tools.train_model import MODEL_VERSION

console = Console()

# How many top-priced drivers count as "favorites" per market.
MARKET_FAVORITE_COUNT = {"race_winner": 3, "podium": 3, "pole": 2, "sprint": 3}
MARKET_ORDER = ["race_winner", "podium", "pole", "sprint"]


# ─────────────────────────────────────────────────────────────────────────────
# Pure decision logic (no DB/IO — unit-tested directly)
# ─────────────────────────────────────────────────────────────────────────────

def classify_decision(oracle, market_mid, bet_size, min_edge: float = MIN_EDGE) -> str:
    """Why the bot did or didn't bet a market, from the facts at bet time.

    Mirrors the live betting gate: a bet needs a live price and a positive edge
    of at least ``min_edge``; joint Kelly can still drop a qualifying market.
    """
    if bet_size and bet_size > 0:
        return "bet"
    if market_mid is None or not (0.0 < market_mid < 1.0):
        return "no price"
    if oracle is None:
        return "no model prob"
    edge = oracle - market_mid
    if edge < 0:
        return "faded (model below market)"
    if edge < min_edge:
        return f"edge {edge * 100:+.1f}% < {min_edge * 100:.0f}% floor"
    return "+edge but dropped by joint Kelly"


def is_faded_favorite(row: dict) -> bool:
    """A favorite the model rated below market (so it could never be a YES bet)."""
    o, m = row.get("oracle"), row.get("market_mid")
    return bool(row.get("is_favorite")) and o is not None and m is not None and o < m


def mark_favorites(rows: list[dict], n: int) -> list[dict]:
    """Tag the ``n`` highest-priced drivers in a market as favorites.

    Mutates and returns the rows. Drivers with no price can't be favorites.
    """
    priced = sorted(
        (r for r in rows if r.get("market_mid") is not None),
        key=lambda r: r["market_mid"],
        reverse=True,
    )
    favs = {id(r) for r in priced[:n]}
    for r in rows:
        r["is_favorite"] = id(r) in favs
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# DB reconstruction
# ─────────────────────────────────────────────────────────────────────────────

def _bet_time(cur, race_id: int):
    """When the bot committed: earliest bet placement, else earliest prediction."""
    cur.execute("""
        SELECT MIN(vb.placed_at)
        FROM virtual_bets vb
        JOIN predictions p ON vb.prediction_id = p.id
        JOIN markets m ON p.market_id = m.id
        WHERE m.race_id = %s
    """, (race_id,))
    row = cur.fetchone()
    if row and row[0] is not None:
        return row[0]
    cur.execute("""
        SELECT MIN(p.predicted_at)
        FROM predictions p JOIN markets m ON p.market_id = m.id
        WHERE m.race_id = %s
    """, (race_id,))
    row = cur.fetchone()
    return row[0] if row else None


def _market_mid_at(cur, market_id: int, when):
    """Real mid for a market from the latest orderbook snapshot at/just before `when`."""
    cur.execute("""
        SELECT best_yes_bid, best_yes_ask, best_no_bid, best_no_ask
        FROM orderbook_snapshots
        WHERE market_id = %s AND snapshot_at <= %s
        ORDER BY snapshot_at DESC LIMIT 1
    """, (market_id, when))
    snap = cur.fetchone()
    if not snap:
        return None
    yb, ya, nb, na = (float(x) if x is not None else None for x in snap)
    if ya is None and nb is not None:
        ya = 1.0 - nb
    if yb is None and na is not None:
        yb = 1.0 - na
    return compute_mid(yb, ya)


def load_weekend(race_id: int, model_version: str = MODEL_VERSION) -> dict | None:
    """Reconstruct the bot's decisions for a race from facts at bet time.

    Returns {race_name, bet_time, by_market: {market_type: [row, ...]}} where each
    row has driver, oracle, market_mid (real, at bet time), edge, bet_size, won,
    position, is_favorite, decision, pnl. Returns None if the race is unknown.
    """
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("SELECT name FROM races WHERE id = %s", (race_id,))
        race = cur.fetchone()
        if not race:
            return None
        race_name = race[0]
        when = _bet_time(cur, race_id)

        cur.execute(
            "SELECT abbreviation, position FROM race_results "
            "WHERE race_id = %s AND position IS NOT NULL", (race_id,))
        race_res = {a: p for a, p in cur.fetchall()}
        cur.execute(
            "SELECT abbreviation, position FROM qualifying_results "
            "WHERE race_id = %s AND position IS NOT NULL", (race_id,))
        quali_res = {a: p for a, p in cur.fetchall()}

        cur.execute("""
            SELECT m.id, m.market_type, m.driver_abbreviation,
                   p.oracle_probability, vb.bet_size_dollars
            FROM markets m
            JOIN predictions p ON p.market_id = m.id AND p.model_version = %s
            LEFT JOIN virtual_bets vb ON vb.prediction_id = p.id
            WHERE m.race_id = %s
        """, (model_version, race_id))
        market_rows = cur.fetchall()

        by_market: dict[str, list[dict]] = {}
        for market_id, mtype, drv, oracle, bet_size in market_rows:
            market_mid = _market_mid_at(cur, market_id, when) if when else None
            oracle = float(oracle) if oracle is not None else None
            bet_size = float(bet_size) if bet_size is not None else 0.0
            won = determine_winner(mtype, drv or "", race_res,
                                   quali_res if quali_res else None)
            pos = (quali_res if mtype == "pole" else race_res).get(drv)
            edge = (oracle - market_mid) if (oracle is not None and market_mid is not None) else None
            pnl = compute_pnl(bet_size, market_mid, won) if (bet_size > 0 and market_mid) else 0.0
            by_market.setdefault(mtype, []).append({
                "driver": drv, "oracle": oracle, "market_mid": market_mid,
                "edge": edge, "bet_size": bet_size, "won": won, "position": pos,
                "pnl": pnl,
            })

    for mtype, rows in by_market.items():
        mark_favorites(rows, MARKET_FAVORITE_COUNT.get(mtype, 3))
        for r in rows:
            r["decision"] = classify_decision(r["oracle"], r["market_mid"], r["bet_size"])

    return {"race_name": race_name, "bet_time": when, "by_market": by_market}


# ─────────────────────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────────────────────

def _pct(x):
    return f"{x * 100:.1f}%" if x is not None else "—"


def _signed(x):
    return f"{x * 100:+.1f}%" if x is not None else "—"


def render(weekend: dict):
    console.print(f"\n[bold cyan]{weekend['race_name']} — Favorites-Faded Review[/]")
    console.print(f"  Prices reconstructed at bet time: [dim]{weekend['bet_time']}[/]")

    # ── Headline: favorites the model faded ──────────────────────────────────
    faded = []
    for mtype in MARKET_ORDER:
        for r in weekend["by_market"].get(mtype, []):
            if is_faded_favorite(r):
                faded.append((mtype, r))

    ft = Table(title="Favorites the model FADED (rated below market → never bettable)",
               header_style="bold", show_header=True)
    ft.add_column("Market", style="cyan")
    ft.add_column("Driver")
    ft.add_column("Oracle", justify="right")
    ft.add_column("Market", justify="right")
    ft.add_column("Edge", justify="right")
    ft.add_column("Result", justify="center")
    for mtype, r in sorted(faded, key=lambda x: -(x[1]["market_mid"] or 0)):
        hit = r["won"]
        result = (f"[red]HIT (P{r['position']})[/]" if hit
                  else f"[dim]miss (P{r['position']})[/]" if r["position"]
                  else "[dim]—[/]")
        ft.add_row(mtype, r["driver"], _pct(r["oracle"]), _pct(r["market_mid"]),
                   _signed(r["edge"]), result)
    if faded:
        console.print(ft)
        burned = [r for _, r in faded if r["won"]]
        if burned:
            names = ", ".join(f"{r['driver']} ({m})" for m, r in faded if r["won"])
            console.print(
                f"  [red bold]✗ {len(burned)} faded favorite(s) hit:[/] {names} — "
                f"the model rated them below the crowd and the crowd was right.")
    else:
        console.print("[green]No favorites were faded this weekend.[/]")

    # ── Full decision table per market ───────────────────────────────────────
    for mtype in MARKET_ORDER:
        rows = weekend["by_market"].get(mtype)
        if not rows:
            continue
        t = Table(title=f"{mtype} — all decisions", header_style="bold", show_header=True)
        t.add_column("Drv", style="cyan")
        t.add_column("Fav", justify="center")
        t.add_column("Oracle", justify="right")
        t.add_column("Market", justify="right")
        t.add_column("Edge", justify="right")
        t.add_column("Bet", justify="right")
        t.add_column("Decision")
        t.add_column("Result", justify="center")
        for r in sorted(rows, key=lambda r: -(r["market_mid"] or 0)):
            result = (f"P{r['position']}" if r["position"] else "—")
            if r["won"]:
                result = f"[green]{result} ✓[/]"
            bet = f"${r['bet_size']:.2f}" if r["bet_size"] > 0 else "—"
            t.add_row(
                r["driver"], "★" if r["is_favorite"] else "",
                _pct(r["oracle"]), _pct(r["market_mid"]), _signed(r["edge"]),
                bet, r["decision"], result,
            )
        console.print(t)

    # ── P&L summary ──────────────────────────────────────────────────────────
    bets = [r for rows in weekend["by_market"].values() for r in rows if r["bet_size"] > 0]
    if bets:
        wins = sum(1 for r in bets if r["won"])
        net = sum(r["pnl"] for r in bets)
        staked = sum(r["bet_size"] for r in bets)
        console.print(
            f"\n[bold]Bets:[/] {wins}/{len(bets)} won · staked ${staked:.2f} · "
            f"net [{'green' if net >= 0 else 'red'}]${net:+.2f}[/]")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--race-id", type=int)
    group.add_argument("--season", type=int)
    parser.add_argument("--round", type=int, dest="round_num")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    args = parser.parse_args()

    if args.race_id:
        race_id = args.race_id
    else:
        if not args.round_num:
            parser.error("--round is required when using --season")
        from tools.db import cursor
        with cursor() as cur:
            cur.execute("SELECT id FROM races WHERE season = %s AND round = %s",
                        (args.season, args.round_num))
            row = cur.fetchone()
        if not row:
            raise ValueError(f"No race found for {args.season} R{args.round_num}")
        race_id = row[0]

    weekend = load_weekend(race_id, args.model_version)
    if weekend is None:
        console.print(f"[red]Race {race_id} not found[/]")
        return
    render(weekend)


if __name__ == "__main__":
    main()
